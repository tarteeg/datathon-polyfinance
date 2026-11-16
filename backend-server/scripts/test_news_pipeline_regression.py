"""Regression tests for the direct-mention / three-tier news pipeline fix.

Run: cd backend-server && set -a && source env && set +a && .venv/bin/python -I scripts/test_news_pipeline_regression.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.riskripple.tools.exposure_tools import load_company_graph
from app.riskripple.alerts.relevance import check_relevance
from app.riskripple.ingestion import news_stocksfeed

results = []


def check(name, condition, detail):
    results.append((name, condition, detail))
    print(("PASS" if condition else "FAIL") + f" | {name} | {detail}")


# 1. A real direct NVIDIA news article (no trade/material vocabulary) must produce a
# match now, even under strict_materials_only (news path).
text = "Prominent NVIDIA investors call for board to contemplate Huang's return"
graph = load_company_graph(["NVDA", "AMD", "ABNB"], event_description=text, strict_materials_only=True)
matches = check_relevance(text, graph, ["NVDA", "AMD", "ABNB"])
check(
    "1. Real direct NVIDIA news (no trade vocabulary) produces a match",
    any(m.symbol == "NVDA" and m.relationship == "direct" for m in matches),
    f"matches={[(m.symbol, m.relationship) for m in matches]}",
)

# 2. AMD's real 10-K naming NVIDIA as a competitor must NOT become a bogus supplier
# edge (regression against the earlier-fixed bug) -- this is a different code path
# (filing-text supplier extraction, not event-text direct-mention) and must be
# unaffected by this fix.
from app.riskripple.graph.company_graph import extract_supplier_edges_from_filing_text, KNOWN_SUPPLIER_ALIASES

amd_filing_snippet = "We compete primarily against Nvidia Corporation in the GPU and AI accelerator market."
edges = extract_supplier_edges_from_filing_text(
    company_symbol="AMD", filing_text=amd_filing_snippet, evidence_label="AMD 10-K", supplier_aliases=KNOWN_SUPPLIER_ALIASES
)
check(
    "2. AMD/NVIDIA competitor mention does not create a bogus supplier edge",
    not any(e.target.lower().startswith("nvidia") for e in edges),
    f"edges={[(e.source, e.target, e.relationship_type) for e in edges]}",
)

# 3. Generic 'semiconductor' keyword overlap must not auto-confirm AAPL -- still
# requires Stage-2 verification (needs_verification=True), same as before this fix.
text3 = "Nvidia and other semiconductor companies rallied today amid AI optimism."
graph3 = load_company_graph(["AAPL"], event_description=text3, strict_materials_only=True)
matches3 = check_relevance(text3, graph3, ["AAPL"])
check(
    "4. Generic 'semiconductor' overlap vs AAPL still requires Stage-2 verification",
    all(m.needs_verification for m in matches3) if matches3 else True,
    f"matches={[(m.symbol, m.needs_verification) for m in matches3]}",
)

# 4. Simulated StocksFeed total failure produces an explicit degraded state, not a
# false empty-success.
import app.integrations.stocksfeed.service as stocksfeed_service


def _raise(*a, **kw):
    raise stocksfeed_service.StocksFeedError("simulated outage")


_orig = stocksfeed_service.fetch_articles
stocksfeed_service.fetch_articles = _raise
try:
    docs, diag = news_stocksfeed.fetch_news_documents_for_tickers_diagnostic(["NVDA", "AMD"], limit_per_ticker=5)
finally:
    stocksfeed_service.fetch_articles = _orig
all_failed = all(d["error"] is not None for d in diag.values())
check(
    "5. Simulated total StocksFeed failure is recorded per-ticker, not silently empty",
    len(docs) == 0 and all_failed,
    f"docs={len(docs)}, diag={diag}",
)

# 5. Person-to-company resolution: "Jensen Huang" alone (no company name at all)
# resolves to NVDA.
text5 = "Jensen Huang steps down amid pressure from the board"
graph5 = load_company_graph(["NVDA", "AMD"], event_description=text5, strict_materials_only=True)
matches5 = check_relevance(text5, graph5, ["NVDA", "AMD"])
check(
    "6. Person-to-company resolution: 'Jensen Huang' alone resolves to NVDA",
    any(m.symbol == "NVDA" and m.relationship == "direct" for m in matches5),
    f"matches={[(m.symbol, m.relationship) for m in matches5]}",
)

print()
if all(r[1] for r in results):
    print("ALL PASSED")
else:
    print("SOME FAILED:", [r[0] for r in results if not r[1]])
    sys.exit(1)

with open(Path(__file__).resolve().parent / "news_pipeline_regression_results.md", "w") as f:
    f.write("# News pipeline (direct-mention / three-tier) regression results\n\n")
    f.write("Real output from `scripts/test_news_pipeline_regression.py`.\n\n")
    for name, ok, detail in results:
        f.write(f"- {'PASS' if ok else 'FAIL'} | {name}\n  - {detail}\n")
