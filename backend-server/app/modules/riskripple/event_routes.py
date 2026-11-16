import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel, Field

from app.modules.chat.routes import model_for_request, require_dashboard
from app.riskripple import event_scan
from app.riskripple.alerts import db
from app.riskripple.personas.profiles import PersonaId
from app.riskripple.scan_run import ScanCache, ScanRun, timestamp

router = APIRouter(prefix="/riskripple/events", tags=["riskripple"])
Ticker = Annotated[str, Field(pattern=r"^[A-Z0-9^][A-Z0-9.^=-]{0,23}$")]
Quantity = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Request(BaseModel):
    persona: PersonaId | None = None
    user_id: str = Field(min_length=1)
    holdings: dict[Ticker, Quantity | None]

    def cache_type(self):
        inputs = json.dumps(self.holdings, sort_keys=True).encode()
        key = "events30:" + hashlib.sha256(inputs).hexdigest()
        return f"{key}:{self.persona.value}" if self.persona else key


def state(request, row):
    return {"status": row["status"] if row else "idle", "result": row["result"] if row else None,
            "updated": row["last_success_at"] if row else None, "error": row["error_message"] if row else None,
            "activity": row.get("activity") if row else None, "empty": not request.holdings}


@router.post("/status")
def status(request: Request, x_chat_key: str = Header(default="")):
    require_dashboard(x_chat_key)
    if not request.holdings:
        return state(request, None)
    key = request.cache_type()
    row = db.get_cached_scan(request.user_id, key)
    if row and row["status"] == "scanning":
        lock = db.lock_event_scan(request.user_id, key)
        if lock is not None:
            try:
                # The worker might have completed between the read and the lock.
                row = db.get_cached_scan(request.user_id, key)
                if row["status"] == "scanning":
                    message = "The scan was interrupted. Start a new scan."
                    if activity := row.get("activity"):
                        for step in activity["steps"]:
                            if step["status"] == "running":
                                step.update(status="unavailable", updated=timestamp())
                        db.save_event_activity(lock, request.user_id, key, activity, status="error", error=message)
                    else:
                        db.save_scan_error(request.user_id, key, message)
                    row = db.get_cached_scan(request.user_id, key)
            finally:
                lock.close()
    return state(request, row)


def finish(request, model, lock, run, *, feed=None, research=None, report=None):
    key = request.cache_type()
    try:
        if report is None:
            if research is not None:
                report = event_scan.apply_persona(research, model, request.persona, run)
            else:
                report = event_scan.scan(request.holdings, model, request.persona, run=run, feed=feed)
        run.publish = None
        run.step("finish", "Report ready", "completed", f"{len(report['events'])} ranked events")
        db.save_event_activity(lock, request.user_id, key, run.activity, status="idle", result=report)
    except Exception as exc:
        logging.getLogger(__name__).exception("Portfolio event scan failed")
        message = str(exc) if isinstance(exc, event_scan.ModelAccessError) else (
            "The scan could not finish. Check the event feed and model access, then retry.")
        run.publish = None
        run.fail(message)
        db.save_event_activity(lock, request.user_id, key, run.activity, status="error", error=message)
    finally:
        lock.close()


@router.post("/scan")
def start(request: Request, tasks: BackgroundTasks, x_chat_key: str = Header(default="")):
    model = model_for_request(x_chat_key)
    if not request.holdings:
        raise HTTPException(422, "Add a holding or watchlist entry before scanning.")
    key = request.cache_type()
    db.ensure_scan_cache_table()
    lock = db.lock_event_scan(request.user_id, key)
    if lock is None:
        return state(request, db.get_cached_scan(request.user_id, key)) | {"status": "scanning"}

    cache = ScanCache(request.user_id, lock)
    run = ScanRun(cache)
    try:
        db.begin_event_run(lock, request.user_id, key, run.activity)
        run.publish = lambda activity: db.save_event_activity(lock, request.user_id, key, activity)
        feed = research = None
        if cache.get(event_scan.research_key(request.holdings, model)):
            run.step("feed", "Check for updated events", "running")
            feed = event_scan.fetch_recent_events()
            run.step("feed", "Check for updated events", "completed", f"{len(feed['events'])} events in the past 30 days")
            research = event_scan.current_research(request.holdings, model, feed, run)
            if research is not None:
                report = event_scan.apply_persona(research, model, request.persona, run, cached_only=True)
                if report is not None:
                    finish(request, model, lock, run, report=report)
                    return state(request, db.get_cached_scan(request.user_id, key))
        response = state(request, db.get_cached_scan(request.user_id, key))
        tasks.add_task(finish, request, model, lock, run, feed=feed, research=research)
        return response
    except Exception:
        try:
            if not lock.closed:
                message = "Could not check current events. Try again."
                run.publish = None
                run.fail(message)
                db.save_event_activity(lock, request.user_id, key, run.activity, status="error", error=message)
        finally:
            lock.close()
        logging.getLogger(__name__).exception("Could not start portfolio event scan")
        return state(request, db.get_cached_scan(request.user_id, key))
