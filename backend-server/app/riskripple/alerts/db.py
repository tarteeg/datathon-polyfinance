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
    PRIMARY KEY (user_id, scan_type)
);
"""


def ensure_scan_cache_table() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_ENSURE_SCAN_CACHE_TABLE_SQL)
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
            "SELECT result_json, status, last_success_at, last_attempt_at, error_message "
            "FROM riskripple_scan_cache WHERE user_id = %s AND scan_type = %s",
            (user_id, scan_type),
        )
        row = cur.fetchone()
        if not row:
            return None
        result_json, status, last_success_at, last_attempt_at, error_message = row
        return {
            "result": result_json,
            "status": status,
            "last_success_at": last_success_at.isoformat() if last_success_at else None,
            "last_attempt_at": last_attempt_at.isoformat() if last_attempt_at else None,
            "error_message": error_message,
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
                (user_id, scan_type, result_json, status, last_success_at, last_attempt_at, error_message)
            VALUES (%s, %s, %s, 'idle', now(), now(), NULL)
            ON CONFLICT (user_id, scan_type) DO UPDATE
            SET result_json = EXCLUDED.result_json, status = 'idle',
                last_success_at = now(), last_attempt_at = now(), error_message = NULL
            """,
            (user_id, scan_type, _json.dumps(result)),
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
