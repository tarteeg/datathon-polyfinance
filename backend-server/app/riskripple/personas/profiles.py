"""The three official PolyFinances Datathon 2026 investor personas (AlphaForge AI
challenge brief) -- NOT the same as the unrelated `PersonaName` (Prudent/Equilibre/
Audacieux) enum in schemas/models.py, which is a French risk-tier taxonomy from an
earlier, since-corrected misunderstanding and is not used by this module.

Amira, Mateo, and Robert are named, specific people with stated constraints in the
brief; the constraints below are this codebase's best-effort encoding of those stated
preferences into checkable numeric limits, not official competition values.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PersonaId(str, Enum):
    AMIRA = "amira"
    MATEO = "mateo"
    ROBERT = "robert"


@dataclass(frozen=True)
class PersonaConstraints:
    persona: PersonaId
    display_name: str
    age: int
    horizon_years: str
    max_equity_allocation: float
    max_single_asset_weight: float
    max_sector_weight: float
    drawdown_tolerance: float  # most negative acceptable historical/scenario drawdown, e.g. -0.20
    min_cash_or_bond_allocation: float
    esg_preference: bool
    description: str


PERSONA_PROFILES: dict[PersonaId, PersonaConstraints] = {
    PersonaId.AMIRA: PersonaConstraints(
        persona=PersonaId.AMIRA,
        display_name="Amira",
        age=26,
        horizon_years="15+ years",
        max_equity_allocation=1.0,
        # Amira explicitly wants growth and emerging tech/crypto exposure but ALSO
        # explicitly does not want to be all-in on one theme -- the brief's own named
        # test for her persona ("account for an aggressive profile without
        # interpreting 'high risk' as 'anything goes'"). This cap is what encodes
        # that diversification requirement even though her equity ceiling is 100%.
        max_single_asset_weight=0.35,
        max_sector_weight=0.60,
        drawdown_tolerance=-0.45,
        min_cash_or_bond_allocation=0.0,
        esg_preference=False,
        description=(
            "High risk tolerance, 15+ year horizon. Seeks growth, emerging technology, and crypto "
            "exposure, but explicitly wants to remain diversified rather than concentrated in one theme."
        ),
    ),
    PersonaId.MATEO: PersonaConstraints(
        persona=PersonaId.MATEO,
        display_name="Mateo",
        age=41,
        horizon_years="8-12 years",
        max_equity_allocation=0.70,
        max_single_asset_weight=0.20,
        max_sector_weight=0.35,
        drawdown_tolerance=-0.20,
        min_cash_or_bond_allocation=0.20,
        esg_preference=True,
        description=(
            "Moderate risk tolerance, 8-12 year horizon. Wants a balance of growth and stability, "
            "with an explicit ESG preference -- environmental, social, and governance controversies matter to him."
        ),
    ),
    PersonaId.ROBERT: PersonaConstraints(
        persona=PersonaId.ROBERT,
        display_name="Robert",
        age=59,
        horizon_years="3-5 years",
        max_equity_allocation=0.40,
        max_single_asset_weight=0.12,
        max_sector_weight=0.20,
        drawdown_tolerance=-0.10,
        min_cash_or_bond_allocation=0.40,
        esg_preference=False,
        description=(
            "Low-to-moderate risk tolerance, 3-5 year horizon. Prioritizes capital preservation, but is "
            "sometimes drawn to a widely publicized, hyped opportunity that conflicts with his own stated profile -- "
            "the brief's own named test is whether the system can challenge that tension rather than simply agree."
        ),
    ),
}


def persona_guidance(persona: PersonaId | None) -> str:
    if persona is None:
        return ""
    profile = PERSONA_PROFILES[persona]
    focus = {
        PersonaId.AMIRA: "Distinguish durable growth from short-term news. Check overlapping business exposures and diversification.",
        PersonaId.MATEO: "Weigh stability against growth. Identify the specific environmental, social or governance evidence, or the disclosure still needed.",
        PersonaId.ROBERT: "Explain downside, income reliability and recovery time in plain language. Put a widely publicized opportunity in the context of its position size.",
    }[persona]
    return (f"Fictional investor: {profile.display_name}. {profile.description} {focus} "
            "Use these preferences only for interpretation and follow-up questions. Keep facts, evidence standards, "
            "and calculations independent of the profile. Do not invent thresholds or recommend trades.")
