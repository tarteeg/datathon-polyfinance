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
