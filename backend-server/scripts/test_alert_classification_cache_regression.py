"""Regression tests for:
1. The 5-level news-exposure classification (verification._classify_direct_news) --
   a materially significant event is NOT automatically a confirmed alert; only a
   concrete, quantified transmission signal is.
2. The scan cache + background-refresh pattern (alerts.db) -- fast placeholder on a
   cold cache, and a failed refresh must never erase a previously successful result.

Run: cd backend-server && set -a && source env && set +a && .venv/bin/python -I scripts/test_alert_classification_cache_regression.py
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")

import boto3

from app.riskripple.alerts import db as alerts_db
from app.riskripple.alerts.relevance import RelevanceMatch
from app.riskripple.alerts.verification import classify_match

results = []


def check(name, condition, detail):
    results.append((name, condition, detail))
    print(f"{'PASS' if condition else 'FAIL'} | {name} | {detail}")


client = boto3.client("bedrock-runtime", region_name="us-east-1")

# --- Test 1: a real, materially significant event with NO quantified signal must
# NOT be confirmed (lands as potential_exposure_unquantified / tier 4). ---
m = RelevanceMatch(
    symbol="NVDA", relationship="direct", node_id="NVDA", matched_entity="NVIDIA",
    evidence_snippet="NVIDIA's Board Was 'Very Deferential' To Jensen Huang: Expert", needs_verification=False,
)
v1 = classify_match(
    client, document_title="NVIDIA's Board Was 'Very Deferential' To Jensen Huang: Expert", match=m,
    industry="Semiconductors", document_source="news",
    document_text="A corporate governance expert said the board's close relationship with Huang may have "
    "delayed succession planning, raising real concerns about leadership transition risk. No stock price "
    "reaction or dollar figure was cited in this report.",
)
check(
    "1. Materially significant event, no quantified signal -> NOT tier 5 (not confirmable)",
    v1.get("classification_tier") != 5,
    f"tier={v1.get('classification_tier')}, classification={v1['classification']}",
)

# --- Test 2: an event WITH an explicit, quantified, attributed price reaction DOES
# qualify for tier 5. ---
m2 = RelevanceMatch(
    symbol="NVDA", relationship="direct", node_id="NVDA", matched_entity="NVIDIA",
    evidence_snippet="Nvidia shares fell sharply", needs_verification=False,
)
v2 = classify_match(
    client, document_title="Nvidia Loses Its Founder: This Week on Wall Street", match=m2,
    industry="Semiconductors", document_source="news",
    document_text="Nvidia shares fell sharply this week after the surprise founder departure announcement, "
    "a decline market commentators explicitly attributed to the leadership change.",
)
check(
    "2. Explicit quantified price reaction attributed to the event -> tier 5 (confirmable)",
    v2.get("classification_tier") == 5,
    f"tier={v2.get('classification_tier')}, classification={v2['classification']}",
)

# --- Test 3: routine noise (earnings beat, no further detail) is dismissed, not even
# a candidate. ---
m3 = RelevanceMatch(
    symbol="AAPL", relationship="direct", node_id="AAPL", matched_entity="Apple",
    evidence_snippet="Apple beats on earnings", needs_verification=False,
)
v3 = classify_match(
    client, document_title="Apple beats on earnings, shares flat", match=m3, industry="Technology",
    document_source="news", document_text="Apple reported quarterly earnings that beat analyst estimates. "
    "Shares were roughly flat in after-hours trading.",
)
check(
    "3. Routine earnings-beat article -> dismissed_insufficient_evidence",
    v3["classification"] == "dismissed_insufficient_evidence",
    f"classification={v3['classification']}",
)

# --- Test 4: regulatory-path direct matches are UNCHANGED (still immediate
# verified_fact, no tier gating applied -- this fix is scoped to news only). ---
m4 = RelevanceMatch(
    symbol="NVDA", relationship="direct", node_id="NVDA", matched_entity="NVIDIA", needs_verification=False,
    evidence_snippet="irrelevant for this path",
)
v4 = classify_match(client, document_title="Some regulatory notice", match=m4, document_source="regulatory")
check(
    "4. Regulatory direct match unaffected by the news-specific tier gate",
    v4["classification"] == "verified_fact" and "classification_tier" not in v4,
    f"classification={v4['classification']}, has_tier_field={'classification_tier' in v4}",
)

# --- Test 5: cache survives a failed refresh. ---
alerts_db.save_scan_success("regression-cache-test", "news", {"articles": [{"title": "real cached article"}]})
before = alerts_db.get_cached_scan("regression-cache-test", "news")
alerts_db.save_scan_error("regression-cache-test", "news", "StocksFeedError: simulated outage")
after = alerts_db.get_cached_scan("regression-cache-test", "news")
check(
    "5. A failed refresh preserves the last successful result and timestamp",
    after["status"] == "error" and after["result"] == before["result"] and after["last_success_at"] == before["last_success_at"],
    f"status={after['status']}, result preserved={after['result'] == before['result']}",
)

# --- Test 6: mark_scan_started doesn't touch a prior successful result either. ---
alerts_db.mark_scan_started("regression-cache-test", "news")
during = alerts_db.get_cached_scan("regression-cache-test", "news")
check(
    "6. A scan-in-progress marker preserves the prior result while status flips to 'scanning'",
    during["status"] == "scanning" and during["result"] == before["result"],
    f"status={during['status']}, result preserved={during['result'] == before['result']}",
)

# cleanup
conn = alerts_db._connect()
cur = conn.cursor()
cur.execute("DELETE FROM riskripple_scan_cache WHERE user_id = %s", ("regression-cache-test",))
conn.commit()
conn.close()

print()
if all(c for _, c, _ in results):
    print("ALL PASSED")
else:
    print("SOME FAILED:", [n for n, c, _ in results if not c])
    sys.exit(1)

with open("scripts/alert_classification_cache_regression_results.md", "w") as f:
    f.write("# Alert classification + scan-cache regression results\n\n")
    for name, cond, detail in results:
        f.write(f"- **{'PASS' if cond else 'FAIL'}** | {name} | {detail}\n")
