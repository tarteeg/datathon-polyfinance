"""Per-account, content-addressed scan artifacts and observable background work."""
import hashlib
import json
import time
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


# Change when prompts, ranking rules, evidence extraction or schemas change.
CACHE_VERSION = 1
FRESH_SECONDS = 300
RESEARCH_SECONDS = 30 * 86400


def digest(*parts):
    encoded = json.dumps([CACHE_VERSION, *parts], sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class ScanCache:
    def __init__(self, user_id=None, connection=None):
        self.user_id = user_id
        self.connection = connection
        self.entries = {}
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            if self.connection is None:
                value = self.entries.get(key)
                return value if value and value[1] > time.time() else None
            with self.connection.cursor() as cur:
                cur.execute("SELECT payload, extract(epoch from expires_at)::float8 FROM riskripple_event_artifacts "
                            "WHERE user_id=%s AND key=%s AND expires_at > now()", (self.user_id, key))
                return cur.fetchone()

    def put(self, key, value, expires=None):
        expires = expires if expires is not None else time.time() + RESEARCH_SECONDS
        with self.lock:
            if self.connection is None:
                self.entries[key] = (value, expires)
            else:
                with self.connection.cursor() as cur:
                    cur.execute("INSERT INTO riskripple_event_artifacts(user_id,key,payload,expires_at) "
                                "VALUES (%s,%s,%s,to_timestamp(%s)) ON CONFLICT(user_id,key) DO UPDATE "
                                "SET payload=excluded.payload,expires_at=excluded.expires_at",
                                (self.user_id, key, json.dumps(value), expires))


class ScanRun:
    def __init__(self, cache=None, publish=None):
        self.cache = cache or ScanCache()
        self.publish = publish
        self.started = time.monotonic()
        self.steps = {}
        self.lock = RLock()
        self.activity = {"id": str(uuid4()), "started": timestamp(), "steps": [], "partial": [],
                         "first_finding_ms": None, "elapsed_ms": 0, "model_calls": 0}

    def model_call(self):
        with self.lock:
            self.activity["model_calls"] += 1

    def step(self, key, title, status, detail="", *, finding=None, done=None, total=None):
        with self.lock:
            at = timestamp()
            step = self.steps.get(key)
            if step is None:
                step = {"key": key, "started": at}
                self.steps[key] = step
                self.activity["steps"].append(step)
            step.update(title=title, status=status, detail=detail, updated=at, done=done, total=total)
            elapsed = round((time.monotonic() - self.started) * 1000)
            self.activity["elapsed_ms"] = elapsed
            if finding is not None:
                self.activity["partial"].append(finding)
                if self.activity["first_finding_ms"] is None:
                    self.activity["first_finding_ms"] = elapsed
            if self.publish:
                self.publish(self.activity)

    def fail(self, message):
        with self.lock:
            for step in self.steps.values():
                if step["status"] == "running":
                    step.update(status="unavailable", updated=timestamp())
            self.step("finish", "Scan interrupted", "unavailable", message)
