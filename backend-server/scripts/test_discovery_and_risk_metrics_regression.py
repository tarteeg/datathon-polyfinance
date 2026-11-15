"""Regression cases for: (1) the cross-portfolio entity-discovery fields on
record_followup_finding being populated when the agent's trace actually names one and
staying empty otherwise, and (2) correlation/drawdown degrading explicitly instead of
crashing or silently omitting when there isn't enough real data.

Run: cd backend-server && set -a && source env && set +a && .venv/bin/python -I scripts/test_discovery_and_risk_metrics_regression.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.riskripple.routes import _build_correlation_and_drawdown, _extract_structured_findings

results = []


def check(name: str, condition: bool, detail: str) -> None:
    status = "PASS" if condition else "FAIL"
    results.append((status, name, detail))
    print(f"{status} | {name} | {detail}")


# --- Case 1: discovered-entity fields populated when the agent's real tool call named one ---
messages_with_discovery = [
    {
        "role": "assistant",
        "content": [
            {
                "toolUse": {
                    "name": "record_followup_finding",
                    "input": {
                        "question": "Does GLOBALFOUNDRIES have Canadian operations?",
                        "tool_used": "search_sec_edgar_live",
                        "classification": "unresolved",
                        "summary": "No hits found; GLOBALFOUNDRIES is private, doesn't file 10-Ks.",
                        "discovered_entity": "GLOBALFOUNDRIES",
                        "discovered_ticker": "GFS",
                        "discovery_relevance": "Named AMD wafer supplier with US fabs; Canada exposure unconfirmed.",
                    }
                }
            }
        ],
    }
]
_, followup, _ = _extract_structured_findings(messages_with_discovery)
check(
    "1. discovered_entity/ticker populated when the real trace named one",
    followup is not None and followup.get("discovered_entity") == "GLOBALFOUNDRIES" and followup.get("discovered_ticker") == "GFS",
    f"followup={followup}",
)

# --- Case 2: fields stay absent/None when the agent's follow-up found nothing new ---
messages_without_discovery = [
    {
        "role": "assistant",
        "content": [
            {
                "toolUse": {
                    "name": "record_followup_finding",
                    "input": {
                        "question": "Does NVDA's 10-K name Microsoft as a revenue-concentration customer?",
                        "tool_used": "search_sec_edgar_live",
                        "classification": "unresolved",
                        "summary": "No hits found naming Microsoft specifically.",
                    }
                }
            }
        ],
    }
]
_, followup2, _ = _extract_structured_findings(messages_without_discovery)
check(
    "2. discovered_entity absent/None when nothing new was found (not forced)",
    followup2 is not None and not followup2.get("discovered_entity"),
    f"followup={followup2}",
)

# --- Case 3: correlation/drawdown degrade explicitly for a single real holding ---
corr_single, dd_single = _build_correlation_and_drawdown(["NVDA"])
check(
    "3. Correlation degrades to an explicit message (not a crash/omission) for 1 holding",
    isinstance(corr_single, str) and "at least 2 holdings" in corr_single,
    f"correlation={corr_single!r}",
)
check(
    "3b. Drawdown still computes for the single real holding that does have history",
    isinstance(dd_single.get("NVDA"), dict) and "max_drawdown_pct" in dd_single.get("NVDA", {}),
    f"drawdown={dd_single}",
)

# --- Case 4: correlation/drawdown degrade explicitly for a fake, unpriceable ticker ---
corr_bad, dd_bad = _build_correlation_and_drawdown(["ZZZZNOTAREALTICKER"])
check(
    "4. Drawdown degrades to an explicit message for a ticker with no real price history",
    isinstance(dd_bad.get("ZZZZNOTAREALTICKER"), str) and "Not enough" in dd_bad.get("ZZZZNOTAREALTICKER", ""),
    f"drawdown={dd_bad}",
)

# --- Case 5: correlation/drawdown compute for real, real-looking 2+ holdings ---
corr_real, dd_real = _build_correlation_and_drawdown(["NVDA", "AMD"])
check(
    "5. Correlation computes a real matrix for 2 real holdings with sufficient history",
    isinstance(corr_real, dict) and "NVDA" in corr_real and "AMD" in corr_real["NVDA"],
    f"correlation={corr_real}",
)

failed = [r for r in results if r[0] == "FAIL"]
print()
print("ALL PASSED" if not failed else f"{len(failed)} FAILED")

out_path = Path(__file__).resolve().parent / "discovery_and_risk_metrics_regression_results.md"
with open(out_path, "w") as f:
    f.write("# Discovery + risk-metrics regression results\n\n")
    f.write("Real output from `scripts/test_discovery_and_risk_metrics_regression.py`.\n\n")
    for status, name, detail in results:
        f.write(f"- **{status}** | {name} | `{detail}`\n")
print(f"\nResults written to {out_path}")

sys.exit(1 if failed else 0)
