"""Minimal read-only connection to the app's real Aurora Postgres database, used only
to discover real per-user portfolios for the alert scan. Deliberately not the ORM/pool
the Next.js frontend uses (`frontend-dashboard/src/lib/db.ts`) -- this is a separate
Python process -- but reads the exact same table (`portfolio_holdings`) with the same
query shape as the frontend's own `getHoldings()` (`src/server/portfolio.ts`), just for
all users at once instead of one session's user.
"""
from __future__ import annotations

import os

import psycopg2


def _connect():
    return psycopg2.connect(
        host=os.environ["DATABASE_HOST"],
        port=os.environ.get("DATABASE_PORT", "5432"),
        dbname=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
        sslmode="require",
        connect_timeout=10,
    )


def get_all_portfolios() -> dict[str, list[str]]:
    """Returns {user_id: [ticker, ticker, ...]} for every real holding currently in
    the database -- the actual thing an alert scan needs to check regulatory/sanctions
    documents against, not a hardcoded demo portfolio.
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, ticker FROM portfolio_holdings ORDER BY user_id, ticker;")
        portfolios: dict[str, list[str]] = {}
        for user_id, ticker in cur.fetchall():
            portfolios.setdefault(user_id, []).append(ticker)
        return portfolios
    finally:
        conn.close()


# Alert deduplication: this app's real shared Aurora Postgres has no alerts table of
# its own yet. Rather than touch any existing table, this adds exactly one small new
# one -- idempotent to create, isolated from everything else in the database -- so a
# repeated scan of the same document against the same (user, symbol) pair doesn't
# produce a duplicate alert every time the scan endpoint is called.
_ENSURE_DEDUP_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS riskripple_alert_dedup (
    document_key TEXT NOT NULL,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (document_key, user_id, symbol)
);
"""


def ensure_dedup_table() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_ENSURE_DEDUP_TABLE_SQL)
        conn.commit()
    finally:
        conn.close()


# Scan result cache: the news scan can take 2-3 minutes (real Bedrock verification
# calls across every genuine candidate found). Running that synchronously on every
# page load is a real UX problem -- confirmed live, 182s for a 3-ticker portfolio.
# This table lets a request return immediately with the last known-good result (even
# if stale) while a background task refreshes it, rather than blocking the caller.
# Same philosophy as the dedup table above: one small, isolated, idempotent table,
# not a general job queue.
_ENSURE_SCAN_CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS riskripple_scan_cache (
    user_id TEXT NOT NULL,
    scan_type TEXT NOT NULL,
    result_json JSONB,
    status TEXT NOT NULL DEFAULT 'idle',
    last_success_at TIMESTAMPTZ,
    last_attempt_at TIMESTAMPTZ,
    error_message TEXT,
    schema_version INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, scan_type)
);
"""

# Confirmed live (2026-11-15): a cache row written by an older backend version --
# before the articles/investigation_candidates/confirmed_alerts three-tier shape
# existed -- was still being served as "fresh" to a real user, showing zero
# confirmed alerts the current code would actually find, because freshness was
# only ever time-based. `schema_version` lets a reader detect "this row predates
# the current response shape" and treat it as stale regardless of its age, without
# needing to disable caching for genuinely current rows. Bump this whenever the
# scan response shape or the logic that decides confirmed/candidate changes.
CURRENT_SCAN_SCHEMA_VERSION = 2  # bumped: regulatory scans now also produce articles/investigation_candidates/confirmed_alerts


def ensure_scan_cache_table() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_ENSURE_SCAN_CACHE_TABLE_SQL)
        # ALTER ... ADD COLUMN IF NOT EXISTS for installs where the table already
        # existed before schema_version was added -- CREATE TABLE IF NOT EXISTS
        # alone won't retrofit existing tables.
        cur.execute("ALTER TABLE riskripple_scan_cache ADD COLUMN IF NOT EXISTS schema_version INTEGER NOT NULL DEFAULT 0;")
        conn.commit()
    finally:
        conn.close()


def get_cached_scan(user_id: str, scan_type: str) -> dict | None:
    """Returns the current cache row for (user_id, scan_type), or None if a scan has
    never been attempted for this pair. Does not trigger anything -- pure read."""
    ensure_scan_cache_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT result_json, status, last_success_at, last_attempt_at, error_message, schema_version "
            "FROM riskripple_scan_cache WHERE user_id = %s AND scan_type = %s",
            (user_id, scan_type),
        )
        row = cur.fetchone()
        if not row:
            return None
        result_json, status, last_success_at, last_attempt_at, error_message, schema_version = row
        return {
            "result": result_json,
            "status": status,
            "last_success_at": last_success_at.isoformat() if last_success_at else None,
            "last_attempt_at": last_attempt_at.isoformat() if last_attempt_at else None,
            "error_message": error_message,
            "schema_version": schema_version,
        }
    finally:
        conn.close()


def mark_scan_started(user_id: str, scan_type: str) -> None:
    """Flips status to 'scanning' and records the attempt time, WITHOUT touching
    result_json or last_success_at -- a previously successful result must stay visible
    and intact while a refresh is in flight."""
    ensure_scan_cache_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO riskripple_scan_cache (user_id, scan_type, status, last_attempt_at)
            VALUES (%s, %s, 'scanning', now())
            ON CONFLICT (user_id, scan_type) DO UPDATE
            SET status = 'scanning', last_attempt_at = now()
            """,
            (user_id, scan_type),
        )
        conn.commit()
    finally:
        conn.close()


def save_scan_success(user_id: str, scan_type: str, result: dict) -> None:
    import json as _json

    ensure_scan_cache_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO riskripple_scan_cache
                (user_id, scan_type, result_json, status, last_success_at, last_attempt_at, error_message, schema_version)
            VALUES (%s, %s, %s, 'idle', now(), now(), NULL, %s)
            ON CONFLICT (user_id, scan_type) DO UPDATE
            SET result_json = EXCLUDED.result_json, status = 'idle',
                last_success_at = now(), last_attempt_at = now(), error_message = NULL,
                schema_version = EXCLUDED.schema_version
            """,
            (user_id, scan_type, _json.dumps(result), CURRENT_SCAN_SCHEMA_VERSION),
        )
        conn.commit()
    finally:
        conn.close()


def save_scan_error(user_id: str, scan_type: str, error_message: str) -> None:
    """Records a failed scan attempt WITHOUT touching result_json or last_success_at
    -- the frontend must be able to keep showing the last good result during a failed
    refresh, not go blank."""
    ensure_scan_cache_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO riskripple_scan_cache (user_id, scan_type, status, last_attempt_at, error_message)
            VALUES (%s, %s, 'error', now(), %s)
            ON CONFLICT (user_id, scan_type) DO UPDATE
            SET status = 'error', last_attempt_at = now(), error_message = EXCLUDED.error_message
            """,
            (user_id, scan_type, error_message),
        )
        conn.commit()
    finally:
        conn.close()


# Manual investigation history: each call to POST /investigate only ever showed its
# result for that one request -- nothing persisted, so there was no way to revisit a
# past manual investigation later. Same minimal, isolated, idempotent-create pattern
# as the other two tables above.
_ENSURE_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS riskripple_investigation_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_description TEXT NOT NULL,
    portfolio_holdings TEXT[] NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def ensure_history_table() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_ENSURE_HISTORY_TABLE_SQL)
        conn.commit()
    finally:
        conn.close()


def save_investigation_history(user_id: str, event_description: str, portfolio_holdings: list[str], result: dict) -> None:
    import json as _json

    ensure_history_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO riskripple_investigation_history "
            "(user_id, event_description, portfolio_holdings, result_json) VALUES (%s, %s, %s, %s)",
            (user_id, event_description, portfolio_holdings, _json.dumps(result)),
        )
        conn.commit()
    finally:
        conn.close()


def list_investigation_history(user_id: str, limit: int = 10) -> list[dict]:
    ensure_history_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT event_description, portfolio_holdings, result_json, created_at "
            "FROM riskripple_investigation_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "event_description": event_description,
                "portfolio_holdings": portfolio_holdings,
                "result": result_json,
                "created_at": created_at.isoformat(),
            }
            for event_description, portfolio_holdings, result_json, created_at in rows
        ]
    finally:
        conn.close()


def filter_unseen(candidates: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """`candidates` is a list of (document_key, user_id, symbol) triples. Returns only
    the ones NOT already recorded as seen, and atomically records all of `candidates`
    as seen in the same call (via `ON CONFLICT DO NOTHING`) -- so a caller that checks
    once and then only acts on the unseen subset can't double-record on a retry, and
    two concurrent scans can't both treat the same pair as unseen.
    """
    if not candidates:
        return []
    ensure_dedup_table()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT document_key, user_id, symbol FROM riskripple_alert_dedup "
            "WHERE (document_key, user_id, symbol) IN %s",
            (tuple(candidates),),
        )
        already_seen = set(cur.fetchall())
        unseen = [c for c in candidates if c not in already_seen]
        cur.executemany(
            "INSERT INTO riskripple_alert_dedup (document_key, user_id, symbol) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            candidates,
        )
        conn.commit()
        return unseen
    finally:
        conn.close()
