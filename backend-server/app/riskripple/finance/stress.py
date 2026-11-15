"""Scenario-based stress testing. All shocks are hypothetical assumptions, never
predictions.

Unlike the sibling riskripple-ai version this was ported from (which hardcoded three
named scenarios against QQQ/SPY only), this version builds a shock scenario from
whatever tickers a user actually holds, driven by a fixed, documented tier->shock
table -- not an LLM-invented percentage. The investigation agent decides WHICH tier
applies to a holding (direct/indirect/unverified/no-link), grounded in its own
evidence-gated classification; this fixed table decides the NUMBER. See
TIER_SHOCKS below.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StressScenario:
    name: str
    description: str
    asset_shocks: dict[str, float]  # e.g. {"NVDA": -0.20} = assumed -20% instantaneous shock
    is_hypothetical: bool = True  # always True; kept explicit so no caller can quietly flip it


@dataclass
class StressTestResult:
    scenario_name: str
    portfolio_value_before: float
    portfolio_pnl: float
    portfolio_value_after: float
    position_pnl: dict[str, float]
    unshocked_assets: list[str]  # assets held but with no shock assumption supplied
    assumptions_label: str = (
        "HYPOTHETICAL SCENARIO: shocks are fixed assumptions tied to the investigation's "
        "own evidence-gated exposure classification, not a model prediction of future returns."
    )


def run_stress_test(
    portfolio_value: float,
    weights: dict[str, float],
    scenario: StressScenario,
) -> StressTestResult:
    """Delta_V = sum_i(position_value_i * assumed_shock_i).

    Assets held in the portfolio but absent from `scenario.asset_shocks` are assumed
    unshocked (0% move) and are reported explicitly in `unshocked_assets` so this
    silent default is never hidden from the caller.
    """
    position_pnl: dict[str, float] = {}
    unshocked = []
    for asset, w in weights.items():
        position_value = portfolio_value * w
        shock = scenario.asset_shocks.get(asset)
        if shock is None:
            shock = 0.0
            unshocked.append(asset)
        position_pnl[asset] = position_value * shock

    total_pnl = sum(position_pnl.values())
    return StressTestResult(
        scenario_name=scenario.name,
        portfolio_value_before=portfolio_value,
        portfolio_pnl=total_pnl,
        portfolio_value_after=portfolio_value + total_pnl,
        position_pnl=position_pnl,
        unshocked_assets=unshocked,
    )


# Fixed, documented tier -> assumed-shock table. The investigation agent assigns each
# holding to exactly one tier via its own evidence-gated classification (see
# tools/portfolio_tools.py's record_exposure_classification); this table is the ONLY
# place a percentage is chosen, and it never changes based on model output -- the
# agent picks the key, not the value. Magnitudes are coarse, illustrative severity
# tiers (not calibrated to any specific historical event) and must always be labeled
# as hypothetical in the UI.
TIER_SHOCKS: dict[str, float] = {
    "direct_verified": -0.20,
    "indirect_evidence_supported": -0.10,
    "unverified_possibility": -0.03,
    "no_established_link": 0.0,
}

TIER_DESCRIPTIONS: dict[str, str] = {
    "direct_verified": "Direct, verified exposure (the event or a verified_fact names this holding/its business directly).",
    "indirect_evidence_supported": "Indirect exposure with real supporting evidence (evidence_supported_hypothesis).",
    "unverified_possibility": "A plausible but unconfirmed connection (unverified_possibility).",
    "no_established_link": "No direct link found in the evidence searched.",
}


def build_tier_shock_scenario(tiers: dict[str, str], *, name: str = "evidence_weighted_shock") -> StressScenario:
    """Build a StressScenario whose asset_shocks come entirely from TIER_SHOCKS,
    keyed by whatever tier each holding (symbol -> tier name) was assigned. Raises on
    an unrecognized tier rather than silently defaulting it, since an unrecognized
    tier is a bug (the agent emitted something outside the fixed vocabulary), not a
    legitimate "no shock" case.
    """
    unknown = {t for t in tiers.values() if t not in TIER_SHOCKS}
    if unknown:
        raise ValueError(f"unrecognized exposure tier(s): {unknown}; must be one of {list(TIER_SHOCKS)}")
    return StressScenario(
        name=name,
        description="Hypothetical shock sized by this investigation's own evidence-gated exposure tier per holding.",
        asset_shocks={symbol: TIER_SHOCKS[tier] for symbol, tier in tiers.items()},
    )
