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
            "empty": not request.holdings}


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
                    db.save_scan_error(request.user_id, key, "The scan was interrupted. Start a new scan.")
                    row = db.get_cached_scan(request.user_id, key)
            finally:
                lock.close()
    return state(request, row)


def run(request, key, model, lock):
    try:
        report = event_scan.scan(request.holdings, model, request.persona)
        db.save_scan_success(request.user_id, key, report)
    except event_scan.ModelAccessError as exc:
        db.save_scan_error(request.user_id, key, str(exc))
    except Exception:
        logging.getLogger(__name__).exception("Portfolio event scan failed")
        db.save_scan_error(request.user_id, key, "The scan could not finish. Check the event feed and model access, then retry.")
    finally:
        lock.close()


@router.post("/scan")
def start(request: Request, tasks: BackgroundTasks, x_chat_key: str = Header(default="")):
    model = model_for_request(x_chat_key)
    if not request.holdings:
        raise HTTPException(422, "Add a holding or watchlist entry before scanning.")
    key = request.cache_type()
    row = db.get_cached_scan(request.user_id, key)
    lock = db.lock_event_scan(request.user_id, key)
    if lock is not None:
        try:
            db.mark_scan_started(request.user_id, key)
            tasks.add_task(run, request, key, model, lock)
        except Exception:
            lock.close()
            raise
    return state(request, row) | {"status": "scanning", "error": None}
