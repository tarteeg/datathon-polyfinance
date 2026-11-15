"""Deterministic (non-LLM) event-briefing aggregation: turns the agent's own real,
already-recorded exposure tiers and portfolio weights into the things a risk/compliance
reader actually needs first -- how much of the portfolio is exposed (by weight, not by
a dollar guess), and what attention level that warrants. This sits ABOVE the existing
hypothetical stress-test dollar figure (finance/stress.py), which stays real and
available but is no longer the headline number: an exposure percentage and an
attention decision are not predictions of loss, just a weighted summary of evidence
already gathered.

Every number here is pure arithmetic over fields the rest of this codebase already
produces (exposure_classifications, portfolio weights) -- no new LLM call, no new
percentage invented. The LLM/agent picks which tier a holding falls into (already
built, evidence-gated); this module only aggregates and classifies, the same
"agent picks the key, fixed code picks the value" split used everywhere else today.
"""
from __future__ import annotations

# Canonical attention-decision vocabulary. Deliberately 4 values, matching the
# product spec -- "no established exposure" is NOT a 5th value, it's the same
# MONITOR/attention_level as a weak/unverified signal would get, distinguished
# instead via the separate `no_established_exposure` boolean below. Collapsing
# "investigated, found nothing" and "investigated, found a weak signal" into one
# attention LEVEL is a deliberate simplification given time constraints -- the
# UI and the explanation text still tell these two cases apart, they just don't
# need a 5th top-level enum value to do it.
ATTENTION_LEVELS = ("ESCALATE", "REVIEW", "MONITOR", "INSUFFICIENT_EVIDENCE")
_ATTENTION_RANK = {"INSUFFICIENT_EVIDENCE": 0, "MONITOR": 1, "REVIEW": 2, "ESCALATE": 3}

_TIER_RANK = {
    "direct_verified": 3,
    "indirect_evidence_supported": 2,
    "unverified_possibility": 1,
    "no_established_link": 0,
}


def exposure_by_weight(weights: dict[str, float], tiers: dict[str, str]) -> dict:
    """Three mutually-exclusive weight buckets -- every holding counted exactly once.
    This is NOT a predicted loss; it is literally "how much of the portfolio, by
    weight, falls into each exposure bucket." Never label this an expected loss.
    """
    direct_pct = sum(w for s, w in weights.items() if tiers.get(s) == "direct_verified")
    potential_pct = sum(
        w for s, w in weights.items() if tiers.get(s) in ("indirect_evidence_supported", "unverified_possibility")
    )
    no_link_pct = sum(w for s, w in weights.items() if tiers.get(s) == "no_established_link")
    affected_holdings = [s for s in weights if tiers.get(s) != "no_established_link"]
    return {
        "direct_exposure_pct": direct_pct,
        "potential_exposure_pct": potential_pct,
        "no_established_link_pct": no_link_pct,
        "affected_holdings": affected_holdings,
        "affected_holdings_count": len(affected_holdings),
    }


def base_attention_level(tiers: dict[str, str]) -> str:
    """ESCALATE if any holding is direct_verified; REVIEW if the strongest tier found
    is indirect_evidence_supported; MONITOR if the strongest is unverified_possibility
    OR if every holding came back no_established_link (a real, checked, negative
    result -- distinguished from INSUFFICIENT_EVIDENCE, which means the event itself
    couldn't even be investigated, via the separate `no_established_exposure` flag
    in `build_event_briefing`, not by a different top-level attention level)."""
    tier_values = set(tiers.values())
    if "direct_verified" in tier_values:
        return "ESCALATE"
    if "indirect_evidence_supported" in tier_values:
        return "REVIEW"
    return "MONITOR"


def persona_attention_level(base: str, *, challenges_the_request: bool) -> str:
    """The SAME real facts, adjusted only by a persona's own already-computed
    constraint signal (`challenges_the_request`, from personas/assessment.py) --
    never adjusted by persona name/identity alone. Only ever raises the level
    (a persona's own risk profile can make something MORE worth attention to them,
    never less, since the underlying evidence didn't change)."""
    if challenges_the_request and _ATTENTION_RANK[base] < _ATTENTION_RANK["REVIEW"]:
        return "REVIEW"
    return base


def build_event_briefing(
    *,
    event_description: str,
    investigation_status: str,  # "completed" | "insufficient_evidence" | "failed"
    tiers: dict[str, str],
    weights: dict[str, float],
    exposure_classifications: dict[str, dict],
    followup_finding: dict | None,
) -> dict:
    """One compact object: what happened, the attention decision, exposure-by-weight,
    why it matters (from the highest-tier holding's own REAL recorded reason -- never
    a new LLM call), and what remains uncertain. `investigation_status` must come from
    the caller (the vague-input guard / agent-call-failure / normal-completion paths
    already distinguish these in routes.py) -- this function doesn't re-derive it,
    only reacts to it, so INSUFFICIENT_EVIDENCE always means "the event itself
    couldn't be classified," never "no holding happened to be exposed."
    """
    if investigation_status != "completed":
        return {
            "what_happened": event_description[:280],
            "investigation_status": investigation_status,
            "attention_level": "INSUFFICIENT_EVIDENCE",
            "no_established_exposure": False,
            "direct_exposure_pct": 0.0,
            "potential_exposure_pct": 0.0,
            "no_established_link_pct": 0.0,
            "affected_holdings": [],
            "affected_holdings_count": 0,
            "why_it_matters": None,
            "uncertain": [],
        }

    exposure = exposure_by_weight(weights, tiers)
    attention = base_attention_level(tiers)
    all_no_link = bool(tiers) and all(t == "no_established_link" for t in tiers.values())

    best_symbol = max(tiers, key=lambda s: _TIER_RANK.get(tiers[s], -1), default=None)
    why_it_matters = None
    if best_symbol is not None and tiers.get(best_symbol) != "no_established_link":
        reason = (exposure_classifications.get(best_symbol, {}) or {}).get("reason", "")
        why_it_matters = reason[:400] if reason else None

    uncertain: list[str] = []
    if followup_finding and followup_finding.get("classification") != "supported":
        uncertain.append(
            f'Follow-up question unresolved: "{followup_finding.get("question", "")}" '
            f"({followup_finding.get('classification')})."
        )
    for symbol, tier in tiers.items():
        if tier == "unverified_possibility":
            uncertain.append(f"{symbol}: only a plausible, unconfirmed connection was found.")

    return {
        "what_happened": event_description[:280],
        "investigation_status": "completed",
        "attention_level": attention,
        "no_established_exposure": all_no_link,
        **exposure,
        "why_it_matters": why_it_matters,
        "uncertain": uncertain[:5],
    }
