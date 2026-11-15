"""Regression tests for app/riskripple/briefing.py (exposure-by-weight + attention
decision). Run with:

    cd backend-server && set -a && source env && set +a && .venv/bin/python -I scripts/test_event_briefing_regression.py

Writes results to scripts/event_briefing_regression_results.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.riskripple.briefing import (
    base_attention_level,
    build_event_briefing,
    exposure_by_weight,
    persona_attention_level,
)

results: list[str] = []


def check(name: str, condition: bool, detail: str) -> None:
    status = "PASS" if condition else "FAIL"
    line = f"{status} | {name} | {detail}"
    print(line)
    results.append(line)


# 1. Exposure weights sum to the total portfolio weight -- every holding counted
# exactly once, across exactly one of the three buckets (never double-counted, never
# dropped).
weights = {"NVDA": 0.5, "AMD": 0.3, "ABNB": 0.2}
tiers = {"NVDA": "direct_verified", "AMD": "indirect_evidence_supported", "ABNB": "no_established_link"}
exposure = exposure_by_weight(weights, tiers)
total = exposure["direct_exposure_pct"] + exposure["potential_exposure_pct"] + exposure["no_established_link_pct"]
check(
    "1. Exposure buckets sum to total portfolio weight, each holding counted once",
    abs(total - sum(weights.values())) < 1e-9 and exposure["direct_exposure_pct"] == 0.5
    and exposure["potential_exposure_pct"] == 0.3 and exposure["no_established_link_pct"] == 0.2,
    f"direct={exposure['direct_exposure_pct']} potential={exposure['potential_exposure_pct']} "
    f"no_link={exposure['no_established_link_pct']} total={total:.6f}",
)

# 2. unverified_possibility is grouped into "potential", not a 4th bucket -- weight-
# change sensitivity: moving weight between tiers shifts the correct bucket only.
weights2 = {"A": 0.4, "B": 0.4, "C": 0.2}
tiers2 = {"A": "indirect_evidence_supported", "B": "unverified_possibility", "C": "no_established_link"}
exposure2 = exposure_by_weight(weights2, tiers2)
check(
    "2. indirect_evidence_supported + unverified_possibility both land in potential_exposure_pct",
    exposure2["potential_exposure_pct"] == 0.8 and exposure2["direct_exposure_pct"] == 0.0,
    f"potential={exposure2['potential_exposure_pct']} direct={exposure2['direct_exposure_pct']}",
)

# 3. affected_holdings excludes no_established_link holdings specifically (not just
# "any holding"), and the count matches the list length.
check(
    "3. affected_holdings excludes no_established_link, count matches list length",
    set(exposure["affected_holdings"]) == {"NVDA", "AMD"} and exposure["affected_holdings_count"] == 2,
    f"affected={exposure['affected_holdings']} count={exposure['affected_holdings_count']}",
)

# 4. base_attention_level: ESCALATE requires at least one direct_verified holding,
# regardless of its weight (a 1% direct-verified position still escalates -- the
# decision is evidence-driven, not weight-driven).
check(
    "4a. Any direct_verified -> ESCALATE even at tiny weight",
    base_attention_level({"TINY": "direct_verified", "BIG": "no_established_link"}) == "ESCALATE",
    "single direct_verified holding present",
)
check(
    "4b. Strongest tier indirect_evidence_supported (no direct_verified) -> REVIEW",
    base_attention_level({"A": "indirect_evidence_supported", "B": "no_established_link"}) == "REVIEW",
    "no direct_verified, one indirect_evidence_supported",
)
check(
    "4c. Strongest tier unverified_possibility -> MONITOR",
    base_attention_level({"A": "unverified_possibility", "B": "no_established_link"}) == "MONITOR",
    "weakest non-zero tier only",
)
check(
    "4d. All holdings no_established_link -> MONITOR (a real negative result, not escalated)",
    base_attention_level({"A": "no_established_link", "B": "no_established_link"}) == "MONITOR",
    "every holding checked and cleared",
)

# 5. Mixed positive/negative/no-link aggregation: tier composition drives the level,
# not any assumption about direction of price impact (this module never looks at
# sign/direction at all -- it only aggregates evidence tiers and weights).
mixed_tiers = {"A": "direct_verified", "B": "indirect_evidence_supported", "C": "unverified_possibility", "D": "no_established_link"}
mixed_weights = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
mixed_exposure = exposure_by_weight(mixed_weights, mixed_tiers)
check(
    "5. Mixed 4-tier portfolio: direct=25%, potential=50% (B+C), no_link=25%, attention=ESCALATE",
    mixed_exposure["direct_exposure_pct"] == 0.25
    and mixed_exposure["potential_exposure_pct"] == 0.5
    and mixed_exposure["no_established_link_pct"] == 0.25
    and base_attention_level(mixed_tiers) == "ESCALATE",
    f"{mixed_exposure}, attention={base_attention_level(mixed_tiers)}",
)

# 6. persona_attention_level only ever raises the level (never lowers it) and only
# when challenges_the_request is True -- the underlying evidence didn't change, so a
# persona's own constraints can't make something LESS worth attention.
check(
    "6a. challenges_the_request=True raises MONITOR -> REVIEW",
    persona_attention_level("MONITOR", challenges_the_request=True) == "REVIEW",
    "base=MONITOR, challenged=True",
)
check(
    "6b. challenges_the_request=True does NOT lower ESCALATE",
    persona_attention_level("ESCALATE", challenges_the_request=True) == "ESCALATE",
    "base=ESCALATE, challenged=True -> stays ESCALATE (already above REVIEW)",
)
check(
    "6c. challenges_the_request=False never changes the base level",
    persona_attention_level("MONITOR", challenges_the_request=False) == "MONITOR"
    and persona_attention_level("ESCALATE", challenges_the_request=False) == "ESCALATE",
    "unchallenged personas see the same base level as everyone else",
)

# 7. build_event_briefing: non-"completed" status never fabricates exposure --
# INSUFFICIENT_EVIDENCE / failed always report 0% everywhere, no affected holdings,
# regardless of what tiers/weights happen to be passed (defensive: caller should pass
# {} but this must not trust that blindly producing a fabricated number instead).
insufficient = build_event_briefing(
    event_description="vague unscoped input",
    investigation_status="insufficient_evidence",
    tiers={"SHOULD_NOT_APPEAR": "direct_verified"},
    weights={"SHOULD_NOT_APPEAR": 1.0},
    exposure_classifications={},
    followup_finding=None,
)
check(
    "7. investigation_status != completed -> zero exposure everywhere, no fabricated loss/exposure",
    insufficient["attention_level"] == "INSUFFICIENT_EVIDENCE"
    and insufficient["direct_exposure_pct"] == 0.0
    and insufficient["affected_holdings"] == []
    and insufficient["affected_holdings_count"] == 0,
    f"{insufficient}",
)

# 8. build_event_briefing on a real completed investigation: why_it_matters comes from
# the highest-tier holding's OWN recorded reason (never fabricated), and "uncertain"
# flags unresolved follow-ups and unverified_possibility tiers.
completed = build_event_briefing(
    event_description="Example sanctions event",
    investigation_status="completed",
    tiers={"NVDA": "direct_verified", "AMD": "unverified_possibility"},
    weights={"NVDA": 0.7, "AMD": 0.3},
    exposure_classifications={
        "NVDA": {"reason": "NVDA named directly in the real sanctions filing."},
        "AMD": {"reason": "Only a plausible competitor linkage, unconfirmed."},
    },
    followup_finding={"question": "Does the order name AMD?", "classification": "unsupported"},
)
check(
    "8. Completed briefing: why_it_matters from the real top-tier reason, uncertain flags both signals",
    completed["why_it_matters"] == "NVDA named directly in the real sanctions filing."
    and completed["attention_level"] == "ESCALATE"
    and completed["direct_exposure_pct"] == 0.7
    and any("unresolved" in u for u in completed["uncertain"])
    and any("AMD" in u and "unconfirmed" in u for u in completed["uncertain"]),
    f"why_it_matters={completed['why_it_matters']!r} uncertain={completed['uncertain']}",
)

# 9. no_established_exposure flag is only True when EVERY holding is no_established_link,
# and is independent of attention_level's own MONITOR value for the same reason (see
# briefing.py's docstring: this is the thing that tells MONITOR-because-nothing-found
# apart from MONITOR-because-weak-signal).
all_clear = build_event_briefing(
    event_description="Checked, nothing found",
    investigation_status="completed",
    tiers={"A": "no_established_link", "B": "no_established_link"},
    weights={"A": 0.5, "B": 0.5},
    exposure_classifications={},
    followup_finding=None,
)
weak_signal = build_event_briefing(
    event_description="Checked, weak signal found",
    investigation_status="completed",
    tiers={"A": "unverified_possibility", "B": "no_established_link"},
    weights={"A": 0.5, "B": 0.5},
    exposure_classifications={},
    followup_finding=None,
)
check(
    "9. no_established_exposure distinguishes true negative from weak-signal MONITOR",
    all_clear["no_established_exposure"] is True
    and weak_signal["no_established_exposure"] is False
    and all_clear["attention_level"] == weak_signal["attention_level"] == "MONITOR",
    f"all_clear.no_established_exposure={all_clear['no_established_exposure']} "
    f"weak_signal.no_established_exposure={weak_signal['no_established_exposure']}",
)

passed = sum(1 for r in results if r.startswith("PASS"))
total_checks = len(results)
summary = f"\n{passed}/{total_checks} checks passed.\n"
print(summary)
results.append(summary)

out_path = Path(__file__).resolve().parent / "event_briefing_regression_results.md"
out_path.write_text(
    "# Event briefing regression results\n\n" + "\n".join(f"- {r}" for r in results[:-1]) + "\n" + results[-1]
)
print(f"Wrote {out_path}")

if passed != total_checks:
    sys.exit(1)
