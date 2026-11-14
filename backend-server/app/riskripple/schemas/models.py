"""Core domain schemas (DynamoDB entity shapes per master spec section 14).

These are the data contracts shared by the API, agents, and Step Functions workflow.
Large blobs (raw documents, reports, datasets) are referenced by S3 key, not embedded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.riskripple.schemas.provenance import SourceMetadata


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class PersonaName(str, Enum):
    PRUDENT = "prudent"
    EQUILIBRE = "equilibre"
    AUDACIEUX = "audacieux"


# English display labels for user-facing text (prose, UI). The enum values above stay
# as-is -- they're used as dict keys/identifiers throughout the backend and in the
# frozen demo fixture -- this is purely for strings a person reads.
PERSONA_DISPLAY_NAMES: dict[str, str] = {
    PersonaName.PRUDENT.value: "Conservative",
    PersonaName.EQUILIBRE.value: "Balanced",
    PersonaName.AUDACIEUX.value: "Aggressive",
}


class Holding(BaseModel):
    symbol: str
    weight: float = Field(ge=0, le=1)
    sector: str | None = None
    currency: str = "USD"


class Portfolio(BaseModel):
    portfolio_id: str = Field(default_factory=lambda: _new_id("ptf"))
    name: str
    base_currency: str = "USD"
    total_value: float = Field(gt=0)
    holdings: list[Holding]
    is_fictional: bool = True  # per spec section 3.2: simulation only, never presented as real
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegulatoryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: _new_id("evt"))
    event_type: str
    title: str
    jurisdiction: str
    effective_date: str | None = None
    publication_date: str | None = None
    affected_entities: list[str] = Field(default_factory=list)
    affected_sectors: list[str] = Field(default_factory=list)
    source_references: list[SourceMetadata] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    processing_status: Literal["new", "investigating", "investigated"] = "new"
    is_simulated: bool = False  # True for the demo's fictional export-restriction scenario


class ExposureEdge(BaseModel):
    source: str
    target: str
    relationship_type: str  # e.g. "supplier", "customer", "etf_holding", "sector_peer"
    evidence_source: str  # human-readable citation, e.g. "NVDA 10-K (0001045810-26-000021)"
    observation_date: str | None = None
    confidence: Literal["verified", "inferred", "unknown"] = "unknown"


class ExposureGraph(BaseModel):
    event_id: str
    nodes: list[str]
    edges: list[ExposureEdge]


class ScenarioDefinition(BaseModel):
    name: str
    description: str
    asset_shocks: dict[str, float]
    is_hypothetical: bool = True


class PersonaConstraints(BaseModel):
    persona: PersonaName
    max_equity_allocation: float
    max_single_asset_weight: float
    max_sector_weight: float
    drawdown_tolerance: float  # most negative acceptable historical max drawdown, e.g. -0.25
    min_cash_or_bond_allocation: float
    description: str


class PersonaEvaluation(BaseModel):
    persona: PersonaName
    proposed_weights: dict[str, float]
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    herfindahl_index: float
    constraint_violations: list[str]
    scenario_pnl: dict[str, float]  # scenario name -> portfolio P&L


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AnalysisResult(BaseModel):
    analysis_id: str = Field(default_factory=lambda: _new_id("ana"))
    portfolio_id: str
    event_id: str | None = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    persona_evaluations: list[PersonaEvaluation] = Field(default_factory=list)
    exposure_graph: ExposureGraph | None = None
    evidence_citations: list[SourceMetadata] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    model_identifier: str | None = None
    calculation_version: str = "finance-engine-0.1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class InvestigationReport(BaseModel):
    report_id: str = Field(default_factory=lambda: _new_id("rpt"))
    analysis_id: str
    investment_question: str
    event_summary: str
    facts: list[str]
    assumptions: list[str]
    hypothetical_scenarios: list[str]
    ai_interpretations: list[str]
    citations: list[SourceMetadata]
    limitations: list[str]
    next_steps: list[str]
    # Optional: populated only when the Ripple Investigation Agent ran (see
    # docs/RIPPLE_INVESTIGATION.md). Additive fields, default empty, so existing
    # reports/fixtures (and the frontend types built against them) stay valid.
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    investigation_trace: list[InvestigationStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEvent(BaseModel):
    audit_id: str = Field(default_factory=lambda: _new_id("aud"))
    analysis_id: str | None = None
    workflow_execution_id: str | None = None
    agent_name: str | None = None
    tool_name: str | None = None
    status: Literal["success", "failure"] = "success"
    duration_ms: float | None = None
    model_identifier: str | None = None
    detail: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RelevanceMatch(BaseModel):
    """One concrete, literal reason a new document was judged relevant to a
    portfolio -- never a similarity score or an LLM guess. See
    riskripple.alerts.relevance."""

    symbol: str
    relationship: Literal["direct", "supply_chain"]
    node_id: str  # the canonical exposure-graph node that matched (== symbol for "direct")
    matched_entity: str  # the literal alias text actually found in the document
    evidence_snippet: str


EvidenceStatus = Literal[
    "verified_fact",  # directly supported by an identified source or deterministic calculation
    "evidence_supported_hypothesis",  # plausible causal mechanism with partial supporting evidence
    "unverified_possibility",  # worth investigating, not established
    "simulated_outcome",  # calculated using explicit assumptions and reproducible code
]


class Hypothesis(BaseModel):
    """One ripple-effect claim produced by the Ripple Investigation Agent (see
    docs/RIPPLE_INVESTIGATION.md), always carrying its evidence status -- a
    hypothesis is never presented with the same confidence as a verified fact.
    A verified competitor relationship does not, by itself, prove a competitor's
    stock price will move; that distinction is what `status` exists to preserve.
    """

    hypothesis_id: str = Field(default_factory=lambda: _new_id("hyp"))
    statement: str
    status: EvidenceStatus
    related_symbols: list[str] = Field(default_factory=list)
    evidence_snippet: str | None = None
    source_tool: str | None = None


class InvestigationStep(BaseModel):
    """One entry in the investigation trace: a single question the Ripple
    Investigation Agent asked, what it did about it, and what it found. Rendered
    directly in the UI per the explainability requirement -- this is structured
    process, not raw model reasoning.
    """

    step_id: str = Field(default_factory=lambda: _new_id("step"))
    question: str
    why_relevant: str
    tools_consulted: list[str] = Field(default_factory=list)
    evidence_found: list[str] = Field(default_factory=list)
    result_status: EvidenceStatus
    follow_up_questions: list[str] = Field(default_factory=list)
    related_symbols: list[str] = Field(default_factory=list)


class Alert(BaseModel):
    """A new regulatory/export-control document judged relevant to a tracked
    portfolio, with the auto-triggered investigation it produced. See
    riskripple.alerts.pipeline and docs/ALERT_PIPELINE.md."""

    alert_id: str = Field(default_factory=lambda: _new_id("alert"))
    document_id: str
    title: str
    source_name: str
    source_url: str
    publication_date: str | None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    matches: list[RelevanceMatch]
    linked_analysis_id: str | None = None
    status: Literal["new", "investigated"] = "new"
