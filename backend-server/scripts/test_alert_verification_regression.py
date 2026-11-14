"""Regression tests for the Stage-1/Stage-2 alert-verification gate (see
app/riskripple/alerts/verification.py), run live against real filing data and a
real Bedrock client. Run with:

    cd backend-server && set -a && source env && set +a \
        && .venv/bin/python -I scripts/test_alert_verification_regression.py

Writes real results to scripts/alert_verification_regression_results.md.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3  # noqa: E402

from app.riskripple.alerts import db as alerts_db  # noqa: E402
from app.riskripple.alerts.pipeline import _generate_recommendation, _is_competitor_relationship  # noqa: E402
from app.riskripple.alerts.relevance import RelevanceMatch, check_relevance  # noqa: E402
from app.riskripple.alerts.verification import classify_match  # noqa: E402
from app.riskripple.tools.exposure_tools import load_company_graph  # noqa: E402

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))
client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

results = []


def record(name, query_desc, expected, actual, passed, latency, detail=""):
    results.append(
        {
            "name": name,
            "query": query_desc,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "latency": latency,
            "detail": detail,
        }
    )
    print(f"{'PASS' if passed else 'FAIL'} | {name} | {actual}")


# --- Case 1: AMD article + generic "semiconductor" overlap with AAPL ---------------
t0 = time.time()
doc_text_1 = (
    "Semiconductor Stocks Rally as AMD Beats Earnings Estimates\n\n"
    "AMD shares rose sharply today after the company beat quarterly earnings "
    "estimates, as semiconductor stocks broadly rallied on strong data-center demand."
)
graph_1 = load_company_graph(["AAPL", "AMD"], event_description=doc_text_1, strict_materials_only=True)
matches_1 = check_relevance(doc_text_1, graph_1, ["AAPL", "AMD"])
aapl_matches_1 = [m for m in matches_1 if m.symbol == "AAPL"]
verdicts_1 = [classify_match(client, document_title=doc_text_1.split("\n")[0], match=m, industry=graph_1["industries"].get("AAPL")) for m in aapl_matches_1]
confirmed_1 = [v for v in verdicts_1 if v["classification"] in ("verified_fact", "evidence_supported_hypothesis")]
latency_1 = time.time() - t0
record(
    "1. AMD article, generic 'semiconductor' overlap with AAPL",
    doc_text_1.split("\n")[0],
    "No confirmed alert for AAPL",
    f"AAPL matches found: {len(aapl_matches_1)}, classifications: {[v['classification'] for v in verdicts_1]}, confirmed: {len(confirmed_1)}",
    len(confirmed_1) == 0,
    latency_1,
    detail=str(verdicts_1),
)

# --- Case 2: real supplier dependency (NVDA/TSMC) must be retained ------------------
t0 = time.time()
doc_text_2 = "Taiwan Semiconductor Manufacturing (TSMC) Reports Record Quarterly Revenue on AI Chip Demand"
graph_2 = load_company_graph(["NVDA"], event_description=doc_text_2, strict_materials_only=True)
matches_2 = check_relevance(doc_text_2, graph_2, ["NVDA"])
verdicts_2 = [classify_match(client, document_title=doc_text_2, match=m, industry=graph_2["industries"].get("NVDA")) for m in matches_2]
confirmed_2 = [v for v in verdicts_2 if v["classification"] in ("verified_fact", "evidence_supported_hypothesis")]
latency_2 = time.time() - t0
record(
    "2. Real NVDA/TSMC supplier dependency retained",
    doc_text_2,
    "At least one confirmed alert (NVDA<->TSMC, a real known-supplier edge)",
    f"matches: {[(m.symbol, m.node_id, m.needs_verification) for m in matches_2]}, confirmed: {len(confirmed_2)}",
    len(confirmed_2) >= 1,
    latency_2,
    detail=str(verdicts_2),
)

# --- Case 3: AMD/NVIDIA competitor relationship, no price-direction language -------
t0 = time.time()
doc_text_3 = (
    "Nvidia Corporation posted strong quarterly results today as demand for "
    "artificial intelligence accelerators continued to grow amid robust customer orders."
)
graph_3 = load_company_graph(["AMD"], event_description=doc_text_3, strict_materials_only=False)
matches_3 = check_relevance(doc_text_3, graph_3, ["AMD"])
competitor_matches = [m for m in matches_3 if _is_competitor_relationship(m)]
rec_text_3 = None
if competitor_matches:
    m = competitor_matches[0]
    verdict_3 = classify_match(client, document_title=doc_text_3, match=m, industry=graph_3["industries"].get("AMD"))
    rec_text_3 = _generate_recommendation(
        client, document_title=doc_text_3, match=m, industry=graph_3["industries"].get("AMD"),
        classification=verdict_3["classification"],
    )
latency_3 = time.time() - t0
price_direction_words = ["bullish", "bearish", "will rise", "will fall", "upside", "downside", "negative for", "positive for", "headwind", "tailwind"]
contains_price_direction = bool(rec_text_3) and any(w in rec_text_3.lower() for w in price_direction_words)
record(
    "3. AMD/NVIDIA competitor relationship, no price-direction claim",
    doc_text_3,
    "Competitor relationship recognized; recommendation contains no price-direction language",
    f"competitor matches: {len(competitor_matches)}, recommendation: {rec_text_3!r}",
    bool(competitor_matches) and not contains_price_direction,
    latency_3,
)

# --- Case 4: generic geographic word "Taiwan" alone is insufficient -----------------
t0 = time.time()
synthetic_match = RelevanceMatch(
    symbol="AAPL",
    relationship="supply_chain",
    node_id="Taiwan",
    matched_entity="Taiwan",
    evidence_snippet="Our regional operations center in Taiwan supports local administrative functions.",
    needs_verification=True,
)
verdict_4 = classify_match(client, document_title="Taiwan's Economy Grows 3% Amid Strong Exports", match=synthetic_match, industry="Retail")
latency_4 = time.time() - t0
record(
    "4. Generic geography word 'Taiwan' alone is insufficient",
    "Taiwan's Economy Grows 3% Amid Strong Exports (vs AAPL, no other specific signal)",
    "unverified_possibility or dismissed_insufficient_evidence (never verified_fact/evidence_supported_hypothesis)",
    verdict_4["classification"],
    verdict_4["classification"] in ("unverified_possibility", "dismissed_insufficient_evidence"),
    latency_4,
    detail=str(verdict_4),
)

# --- Case 5: duplicate scan of the same article/company does not double-alert ------
t0 = time.time()
doc_key = "test-dedup-doc-001"
first_pass = alerts_db.filter_unseen([(doc_key, "test-user", "NVDA")])
second_pass = alerts_db.filter_unseen([(doc_key, "test-user", "NVDA")])
latency_5 = time.time() - t0
record(
    "5. Duplicate scan does not re-alert (dedup table)",
    f"filter_unseen called twice with identical ({doc_key}, test-user, NVDA)",
    "First call returns it as unseen; second call returns empty",
    f"first={first_pass}, second={second_pass}",
    first_pass == [(doc_key, "test-user", "NVDA")] and second_pass == [],
    latency_5,
)

# Cleanup the synthetic dedup row so this test is safely re-runnable and doesn't
# leave synthetic data in the real shared database.
try:
    conn = alerts_db._connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM riskripple_alert_dedup WHERE user_id = %s", ("test-user",))
    conn.commit()
    conn.close()
except Exception as exc:
    print(f"cleanup warning: {exc}")

# --- Write results file -------------------------------------------------------------
lines = ["# Alert verification regression results\n",
         "Real output from `scripts/test_alert_verification_regression.py`, run live "
         "against real filings, a real Bedrock client, and the real (now cleaned-up) "
         "dedup table on 2026-11-14.\n", "\n## Summary\n",
         "| Case | Passed | Latency |", "|---|---|---|"]
for r in results:
    lines.append(f"| {r['name']} | {'PASS' if r['passed'] else 'FAIL'} | {r['latency']:.2f}s |")
lines.append("\n## Detail\n")
for r in results:
    lines.append(f"### {r['name']}")
    lines.append(f"- Query/case: {r['query']}")
    lines.append(f"- Expected: {r['expected']}")
    lines.append(f"- Actual: {r['actual']}")
    lines.append(f"- Passed: {r['passed']}")
    if r["detail"]:
        lines.append(f"- Detail: {r['detail']}")
    lines.append("")

out_path = os.path.join(os.path.dirname(__file__), "alert_verification_regression_results.md")
with open(out_path, "w") as f:
    f.write("\n".join(lines))

all_passed = all(r["passed"] for r in results)
print(f"\n{'ALL PASSED' if all_passed else 'SOME FAILED'} -- results written to {out_path}")
sys.exit(0 if all_passed else 1)
