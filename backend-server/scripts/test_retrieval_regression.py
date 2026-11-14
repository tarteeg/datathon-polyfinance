"""Retrieval regression harness, run manually (not pytest): compares the lexical-only
retriever against the Bedrock/hybrid path on real cases this session found failing,
plus a false-positive and a genuine-negative case. Every result below is real output
from an actual run against the live Knowledge Base and real SEC filings -- see
retrieval_regression_results.md for the recorded run this script produced.

Run: cd backend-server && set -a && source env && set +a && .venv/bin/python -I scripts/test_retrieval_regression.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.riskripple.tools.exposure_tools import hybrid_search_evidence
from app.riskripple.tools.regulatory_tools import summarize_event_evidence

CASES = [
    {
        "name": "NVDA export controls",
        "query": "export controls and sanctions risk for semiconductor companies",
        "symbol": "NVDA",
        "expected_passage_contains": "export control",
    },
    {
        "name": "AMD export controls / Entity List",
        "query": "Uyghur Forced Labor Prevention Act Entity List",
        "symbol": "AMD",
        "expected_passage_contains": "entity list",
    },
    {
        "name": "JPM Russia sanctions",
        "query": "Russia sanctions and geopolitical risk",
        "symbol": "JPM",
        "expected_passage_contains": "geopolitical",
    },
    {
        "name": "AEE coal-fired plant regulation",
        "query": "Coal-fired power plant environmental regulations",
        "symbol": "AEE",
        "expected_passage_contains": "environmental",
    },
    {
        "name": "INTC rare earth",
        "query": "rare earth element and mineral supply chain concentration",
        "symbol": "INTC",
        "expected_passage_contains": "rare earth",
    },
    {
        "name": "INTC ASML EUV lithography",
        "query": "ASML EUV lithography equipment dependency",
        "symbol": "INTC",
        "expected_passage_contains": "asml",
    },
    {
        "name": "False positive: generic procedural phrase",
        "query": "Introduction to the Unified Agenda of Federal Regulatory and Deregulatory Actions",
        "symbol": "NVDA",
        "expected_passage_contains": None,  # should NOT produce a confident literal match
        "is_false_positive_check": True,
    },
    {
        "name": "Genuine negative: unrelated holding/event",
        "query": "professional sports league broadcasting rights renegotiation",
        "symbol": "AEE",
        "expected_passage_contains": None,
        "is_negative_check": True,
    },
]


def run_case(case: dict) -> dict:
    query, symbol = case["query"], case["symbol"]

    # Force lexical-only by clearing the KB id for this one call.
    os.environ["RISKRIPPLE_KNOWLEDGE_BASE_ID"] = ""
    t0 = time.time()
    lexical = summarize_event_evidence(event_title=query, filing_symbol=symbol)
    lexical_latency = time.time() - t0

    os.environ.pop("RISKRIPPLE_KNOWLEDGE_BASE_ID", None)  # restore default (Bedrock)
    t0 = time.time()
    hybrid = hybrid_search_evidence(query=query, filing_symbol=symbol)
    hybrid_latency = time.time() - t0

    def _rank_of(text: str, needle: str | None) -> int | None:
        if not needle or not text:
            return None
        lower = text.lower()
        idx = lower.find(needle.lower())
        return 1 if idx != -1 and idx < 2000 else (0 if idx == -1 else 2)  # crude: top-of-context vs. present-but-later

    expected = case.get("expected_passage_contains")
    return {
        "name": case["name"],
        "query": query,
        "symbol": symbol,
        "expected_contains": expected,
        "lexical_found": lexical.get("found"),
        "lexical_latency_s": round(lexical_latency, 3),
        "lexical_excerpt": (lexical.get("evidence_context") or "")[:200],
        "lexical_rank": _rank_of(lexical.get("evidence_context", ""), expected),
        "hybrid_found": hybrid.get("found"),
        "hybrid_latency_s": round(hybrid_latency, 3),
        "hybrid_retriever_used": hybrid.get("semantic_retriever_used"),
        "hybrid_literal_matches": hybrid.get("literal_matches"),
        "hybrid_semantic_excerpt": (hybrid.get("semantic_evidence") or "")[:200],
        "hybrid_rank": _rank_of((hybrid.get("semantic_evidence") or "") + str(hybrid.get("literal_matches")), expected),
        "citation_has_real_source": "s3://" in (hybrid.get("semantic_evidence") or "") or "sec.gov" in (hybrid.get("semantic_evidence") or "") or bool(hybrid.get("literal_matches")),
    }


if __name__ == "__main__":
    results = [run_case(c) for c in CASES]
    import json

    print(json.dumps(results, indent=2, default=str))
