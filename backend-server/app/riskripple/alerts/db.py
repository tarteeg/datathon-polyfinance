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
