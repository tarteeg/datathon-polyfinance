"""Deterministic (non-LLM) persona-fit assessment. Given the SAME real portfolio
weights and the SAME investigation findings (exposure tiers per holding, real
industries, real volatility, the scenario-shock result), produce a genuinely distinct,
rule-based assessment per official persona -- never three rephrasings of one paragraph,
because the underlying numeric comparisons (each persona's own constraints) differ.

Text is built from f-string templates over real numbers, not a separate LLM call --
this guarantees the three outputs are substantively different whenever the inputs
differ, and keeps every number traceable to a specific constraint/calculation rather
than to model wording choices.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.riskripple.personas.profiles import PERSONA_PROFILES, PersonaConstraints, PersonaId


@dataclass
class PersonaAssessment:
    persona: str
    display_name: str
    description: str
    constraint_violations: list[str] = field(default_factory=list)
    esg_notes: list[str] = field(default_factory=list)
    verdict: str = ""
    challenges_the_request: bool = False


def _sector_concentration(weights: dict[str, float], industries: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for symbol, w in weights.items():
        sector = industries.get(symbol) or "Unknown industry"
        out[sector] = out.get(sector, 0.0) + w
    return out


def _check_violations(
    constraints: PersonaConstraints,
    weights: dict[str, float],
    industries: dict[str, str],
    scenario_pnl_pct: float | None,
) -> list[str]:
    violations: list[str] = []
    if not weights:
        return violations

    # This codebase does not currently model cash/bond holdings for a real user's
    # portfolio (only equity positions are tracked) -- so a 100%-equity portfolio is
    # compared directly against each persona's equity ceiling, which is itself a real,
    # meaningful finding for Mateo and Robert (both have ceilings well below 100%),
    # not an artifact.
    equity_weight = sum(weights.values())
    if equity_weight > constraints.max_equity_allocation + 1e-6:
        violations.append(
            f"This portfolio is {equity_weight:.0%} invested in equities with no tracked cash/bond "
            f"allocation, exceeding {constraints.display_name}'s stated equity ceiling of "
            f"{constraints.max_equity_allocation:.0%}."
        )

    largest_symbol = max(weights, key=weights.get)
    largest_weight = weights[largest_symbol]
    if largest_weight > constraints.max_single_asset_weight + 1e-6:
        violations.append(
            f"{largest_symbol} alone is {largest_weight:.0%} of the portfolio, exceeding "
            f"{constraints.display_name}'s single-position limit of {constraints.max_single_asset_weight:.0%}."
        )

    for sector, w in _sector_concentration(weights, industries).items():
        if w > constraints.max_sector_weight + 1e-6:
            violations.append(
                f"{w:.0%} of the portfolio is concentrated in \"{sector}\", exceeding "
                f"{constraints.display_name}'s sector concentration limit of {constraints.max_sector_weight:.0%}."
            )

    if scenario_pnl_pct is not None and scenario_pnl_pct < constraints.drawdown_tolerance - 1e-9:
        violations.append(
            f"The hypothetical scenario shock to this portfolio ({scenario_pnl_pct:.1%}) exceeds "
            f"{constraints.display_name}'s stated drawdown tolerance of {constraints.drawdown_tolerance:.0%}."
        )

    return violations


def assess_persona_fit(
    persona_id: PersonaId,
    *,
    weights: dict[str, float],
    weights_are_real: bool,
    industries: dict[str, str],
    tiers: dict[str, str],
    scenario_pnl_pct: float | None,
    esg_evidence_found: dict[str, bool] | None = None,
) -> PersonaAssessment:
    constraints = PERSONA_PROFILES[persona_id]
    esg_evidence_found = esg_evidence_found or {}

    violations = _check_violations(constraints, weights, industries, scenario_pnl_pct)

    exposed_symbols = [s for s, t in tiers.items() if t in ("direct_verified", "indirect_evidence_supported")]

    esg_notes: list[str] = []
    if constraints.esg_preference and exposed_symbols:
        missing = [s for s in exposed_symbols if not esg_evidence_found.get(s, False)]
        if missing:
            esg_notes.append(
                f"{constraints.display_name} has an explicit ESG preference, but this investigation did not "
                f"find ESG-relevant disclosure for {', '.join(missing)}. This is a real evidence gap, not an "
                f"ESG judgment -- it should not be read as either a pass or a fail on {constraints.display_name}'s "
                "ESG criterion."
            )

    weight_basis = (
        "based on your real current portfolio weights"
        if weights_are_real
        else "using an assumed equal weighting, since real position sizes were not provided for this request"
    )

    challenges = False
    if violations:
        if persona_id == PersonaId.ROBERT:
            challenges = True
            verdict = (
                f"This does not fit {constraints.display_name}'s stated profile ({weight_basis}). "
                f"{constraints.description} " + " ".join(violations) + " "
                f"Given his short horizon and capital-preservation objective, the system should flag this "
                "tension rather than simply describe the event neutrally."
            )
        elif persona_id == PersonaId.AMIRA:
            verdict = (
                f"{constraints.display_name} has a high risk tolerance and a 15+ year horizon, so the exposure "
                f"itself is not automatically disqualifying ({weight_basis}). However: " + " ".join(violations) + " "
                f"{constraints.display_name} has specifically said she wants to remain diversified even while "
                "pursuing growth, so concentration like this is worth surfacing to her explicitly."
            )
        else:
            verdict = (
                f"This portfolio currently exceeds one or more of {constraints.display_name}'s stated limits "
                f"({weight_basis}): " + " ".join(violations)
            )
    else:
        verdict = (
            f"No stated constraint of {constraints.display_name}'s is currently violated by this portfolio "
            f"({weight_basis})."
        )

    if esg_notes:
        verdict = verdict + " " + " ".join(esg_notes)

    return PersonaAssessment(
        persona=persona_id.value,
        display_name=constraints.display_name,
        description=constraints.description,
        constraint_violations=violations,
        esg_notes=esg_notes,
        verdict=verdict,
        challenges_the_request=challenges,
    )


def compare_personas(
    *,
    weights: dict[str, float],
    weights_are_real: bool,
    industries: dict[str, str],
    tiers: dict[str, str],
    scenario_pnl_pct: float | None,
    esg_evidence_found: dict[str, bool] | None = None,
) -> list[PersonaAssessment]:
    return [
        assess_persona_fit(
            pid,
            weights=weights,
            weights_are_real=weights_are_real,
            industries=industries,
            tiers=tiers,
            scenario_pnl_pct=scenario_pnl_pct,
            esg_evidence_found=esg_evidence_found,
        )
        for pid in (PersonaId.AMIRA, PersonaId.MATEO, PersonaId.ROBERT)
    ]
