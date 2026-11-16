"""The "watch and react" loop: for each real user's real portfolio, check incoming
regulatory/sanctions documents for genuine relevance (via the same evidence-gated
exposure graph the on-demand /riskripple/investigate route uses) and, for anything
relevant, generate a short, constrained recommendation.

Adapted from riskripple-ai's `alerts/pipeline.py`, which was built against a single
hardcoded demo portfolio and a DynamoDB store. This version runs against every real
portfolio currently in the app's own Postgres database (`alerts.db.get_all_portfolios`)
and does not persist anything -- see `run_alert_scan`'s docstring for why.

The recommendation step deliberately does NOT run a full Bedrock/Strands agent per
document per portfolio: the existing /riskripple/investigate agent run takes ~70s per
call (confirmed in prior live testing), which would make scanning N documents across
M portfolios take N*M*70s -- impractical for a scan endpoint. Instead it makes one
direct, non-agentic Bedrock `converse` call per relevant match, grounded only in the
already-gathered evidence (the matched document text + the real filing evidence
snippet), with an explicit system prompt enforcing the same responsible-use
constraints as the rest of this codebase (simulation-only, no trade advice).
"""
from __future__ import annotations

import os

import boto3

from app.riskripple.personas.profiles import PersonaId, persona_guidance
from app.riskripple.alerts import db as alerts_db
from app.riskripple.alerts.relevance import RelevanceMatch, check_relevance
from app.riskripple.alerts.verification import classify_match
from app.riskripple.tools.exposure_tools import load_company_graph

# Only these classifications are confirmed enough to record as an alert. A Stage-2
# "unverified_possibility" is still returned to the caller (labeled as a hypothesis,
# never as an alert), and "dismissed_insufficient_evidence" is dropped entirely --
# see alerts.verification.classify_match.
_ALERT_WORTHY_CLASSIFICATIONS = {"verified_fact", "evidence_supported_hypothesis"}


def _consolidate_matches_by_symbol(matches: list[RelevanceMatch]) -> list[RelevanceMatch]:
    """`check_relevance` can return more than one RelevanceMatch for the same symbol
    against the same document -- e.g. one "direct" match (the company's own name
    found in the text) and a separate "supply_chain" match (a generic candidate term
    also found) -- because they come from different graph nodes and are deduplicated
    independently per relationship type. Left unconsolidated, each gets classified on
    its own and can produce contradictory verdicts for the same (document, symbol)
    pair (confirmed live: one classified `unverified_possibility`/not confirmed, the
    other `evidence_supported_hypothesis`/confirmed, for the identical article and
    company). Pick exactly one representative match per symbol before classification:
    a "direct" match wins outright (it already answers "is this about the company"),
    otherwise prefer a specific-term match (needs_verification=False) over a
    generic-candidate one, and fold any other matches' evidence into it so no signal
    is silently dropped.
    """
    by_symbol: dict[str, list[RelevanceMatch]] = {}
    for m in matches:
        by_symbol.setdefault(m.symbol, []).append(m)

    consolidated: list[RelevanceMatch] = []
    for symbol, group in by_symbol.items():
        if len(group) == 1:
            consolidated.append(group[0])
            continue
        direct = next((m for m in group if m.relationship == "direct"), None)
        primary = direct or next((m for m in group if not m.needs_verification), None) or group[0]
        others = [m for m in group if m is not primary]
        if others:
            extra_entities = ", ".join(dict.fromkeys(m.matched_entity for m in others if m.matched_entity != primary.matched_entity))
            extra_snippets = " | ".join(dict.fromkeys(m.evidence_snippet for m in others if m.evidence_snippet != primary.evidence_snippet))
            primary = RelevanceMatch(
                symbol=primary.symbol,
                relationship=primary.relationship,
                node_id=primary.node_id,
                matched_entity=primary.matched_entity + (f" (also: {extra_entities})" if extra_entities else ""),
                evidence_snippet=primary.evidence_snippet + (f" | Additional evidence: {extra_snippets}" if extra_snippets else ""),
                needs_verification=primary.needs_verification,
            )
        consolidated.append(primary)
    return consolidated

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))

RECOMMENDATION_SYSTEM_PROMPT = """You are RiskRipple AI's alert-recommendation writer.
You are given: a news article or regulatory/sanctions document, a specific real
portfolio holding it has been matched to (directly or via a real, evidence-based
supply-chain/material/competitor link), the exact evidence snippet that justified the
match, its verification classification, and optionally the holding's real recent
price move. Write a 2-3 sentence recommendation for the portfolio holder.

Rules, no exceptions:
- Simulation/informational only. NEVER suggest buying, selling, or any specific trade
  or portfolio action. Do not use the words "buy", "sell", "should", or "recommend
  trading" in any form.
- Only reference the specific evidence given to you. Do not invent facts, sources, or
  numbers not present in the input.
- Frame it as "what this means for this holding" and "what to watch for" -- e.g.
  reviewing sector concentration, monitoring further developments, or reading the
  underlying filing -- never as investment advice.
- If the evidence is only a plausible/indirect link (relationship == "supply_chain"),
  say so explicitly; do not overstate certainty. If the classification is
  "unverified_possibility", say explicitly that this is a hypothesis, not a confirmed
  link.
- If the matched entity is a disclosed COMPETITOR (not a supplier or material
  dependency), state the competitive relationship as a fact only -- NEVER imply,
  suggest, or hint at any directional stock-price impact (positive or negative) from
  a competitor's news. A competitor relationship existing is not evidence of which
  way either company's price will move.
- If a real recent price move is given, state it only as context ("the stock has
  already moved X% over the period") -- never as a signal to act on, and never imply
  the move was caused by this specific document unless the evidence says so."""


def _price_move_note(symbol: str) -> str | None:
    """A real, recent price move for `symbol`, as plain context -- not a trading
    signal. Uses the same Yahoo integration the frontend's own stock pages already
    call. Returns None (rather than raising) on any failure -- rate limits or an
    unrecognized ticker shouldn't fail the whole alert scan, and callers must not
    fabricate a number when this returns None.
    """
    try:
        from app.integrations.yahoo.service import fetch_history

        history = fetch_history(symbol, "5d")
    except Exception:
        return None
    candles = history.get("candles") or []
    if len(candles) < 2:
        return None
    first_close, last_close = candles[0]["Close"], candles[-1]["Close"]
    if not first_close:
        return None
    pct = (last_close - first_close) / first_close * 100
    currency = history["ticker"].get("currency") or ""
    return f"{symbol} has moved {pct:+.1f}% over the past 5 trading days ({currency} terms)."


def _is_competitor_relationship(match: RelevanceMatch) -> bool:
    """A match whose target is itself a known public COMPANY (per
    `exposure_tools.KNOWN_COMPANY_NAMES`) rather than a known SUPPLIER (per
    `company_graph.KNOWN_SUPPLIER_ALIASES`) is a peer/competitor-style mention, not a
    supply-chain dependency -- e.g. AMD's real 10-K naming NVIDIA as a competitor it
    "compete[s] primarily against". This only flags node_ids this codebase already
    has on record as a real company; it does not newly infer anything."""
    from app.riskripple.graph.company_graph import KNOWN_SUPPLIER_ALIASES
    from app.riskripple.tools.exposure_tools import KNOWN_COMPANY_NAMES

    node_lower = match.node_id.lower()
    is_known_company = node_lower in {k.lower() for k in KNOWN_COMPANY_NAMES} or node_lower in {
        v.lower() for v in KNOWN_COMPANY_NAMES.values()
    }
    is_known_supplier = node_lower in {k.lower() for k in KNOWN_SUPPLIER_ALIASES}
    return is_known_company and not is_known_supplier


def _generate_recommendation(
    client,
    *,
    document_title: str,
    match: RelevanceMatch,
    industry: str | None,
    classification: str,
    price_note: str | None = None,
    persona: PersonaId | None = None,
) -> str:
    if match.relationship == "direct":
        relationship_note = "a direct mention of this holding"
    elif _is_competitor_relationship(match):
        relationship_note = f"a disclosed COMPETITOR relationship with '{match.node_id}' (not a supplier/material link)"
    else:
        relationship_note = f"an indirect supply-chain/material link via '{match.node_id}'"
    user_text = (
        f"Document: {document_title}\n"
        f"Portfolio holding: {match.symbol}"
        + (f" (SEC industry: {industry})" if industry else "")
        + f"\nMatch type: {relationship_note}\n"
        f"Verification classification: {classification}\n"
        f"Evidence snippet actually found: \"{match.evidence_snippet}\""
        + (f"\nReal recent price context: {price_note}" if price_note else "")
        + "\n\nWrite the recommendation now."
    )
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": RECOMMENDATION_SYSTEM_PROMPT + "\n" + persona_guidance(persona)}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.2},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def run_alert_scan(
    *,
    documents: list[dict],
    portfolios: dict[str, list[str]],
    bedrock_client=None,
    strict_materials_only: bool = False,
    deduplicate: bool = True,
    persona: PersonaId | None = None,
) -> list[dict]:
    """`documents` is a list of {"document_number", "title", "abstract", ...} (the
    shape `ingestion.regulatory_events.search_documents*` returns, as plain dicts).
    `portfolios` is {user_id: [ticker, ...]}, as `alerts.db.get_all_portfolios`
    returns.

    Each Stage-1 candidate match is passed through Stage-2 verification
    (`alerts.verification.classify_match`) before being treated as an alert: a
    `verified_fact` or `evidence_supported_hypothesis` match is recorded as a
    confirmed alert; an `unverified_possibility` match is still returned (so a
    genuinely new, specific-but-thin cross-industry relationship the curated
    denylists don't anticipate isn't silently discarded) but explicitly marked
    `is_confirmed_alert: False` rather than treated as one; a
    `dismissed_insufficient_evidence` match (coincidental generic-word overlap, the
    false-positive failure mode this gate exists to catch) is dropped before even
    generating a recommendation, saving that Bedrock call entirely.

    `deduplicate=True` (default) records each (document, user, symbol) triple in a
    small Postgres table (`alerts.db`) so re-scanning the same document against the
    same holding doesn't produce a duplicate alert on a later call. Pass `False` only
    for isolated testing that shouldn't touch the real database.
    """
    client = bedrock_client or boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    price_note_cache: dict[str, str | None] = {}

    def _cached_price_note(symbol: str) -> str | None:
        if symbol not in price_note_cache:
            price_note_cache[symbol] = _price_move_note(symbol)
        return price_note_cache[symbol]

    alerts: list[dict] = []
    # Build each portfolio's exposure graph once per document (not once per portfolio
    # total), since the graph is event_description-specific -- it must be rebuilt
    # per document, but is naturally reused across nothing else here.
    for doc in documents:
        doc_text = f"{doc.get('title', '')}\n\n{doc.get('abstract') or ''}"
        for user_id, symbols in portfolios.items():
            if not symbols:
                continue
            graph_json = load_company_graph(
                portfolio_symbols=symbols, event_description=doc_text, strict_materials_only=strict_materials_only
            )
            matches = check_relevance(doc_text, graph_json, symbols)
            if not matches:
                continue  # genuinely not relevant to this user's holdings -- correctly suppressed
            matches = _consolidate_matches_by_symbol(matches)

            doc_key = doc.get("document_number") or doc.get("title", "")
            if persona:
                doc_key = f"{doc_key}:{persona.value}"
            if deduplicate:
                candidates = [(doc_key, user_id, m.symbol) for m in matches]
                unseen_keys = {(s,) for (_, _, s) in alerts_db.filter_unseen(candidates)}
                matches = [m for m in matches if (m.symbol,) in unseen_keys]
                if not matches:
                    continue  # every match here was already recorded by an earlier scan

            industries = graph_json.get("industries", {})
            recommendations = []
            for m in matches:
                verdict = classify_match(
                    client,
                    document_title=doc.get("title", ""),
                    match=m,
                    industry=industries.get(m.symbol),
                    document_source=doc.get("source", "regulatory"),
                    document_text=doc_text,
                )
                classification = verdict["classification"]
                if classification == "dismissed_insufficient_evidence":
                    # Coincidental generic-word overlap, no real mechanism -- the
                    # exact false-positive failure mode Stage 2 exists to catch.
                    # Dropped before spending a recommendation-generation call.
                    continue
                # A direct news mention's materiality (classification in
                # _ALERT_WORTHY_CLASSIFICATIONS) is NOT by itself sufficient to
                # confirm a portfolio-exposure alert -- confirmed live: 3 real
                # Jensen-Huang/NVIDIA leadership-crisis stories were reaching
                # confirmed_alerts on materiality alone. For this specific path
                # (news + direct), require the stricter classification_tier==5
                # ("evidence_supported_portfolio_exposure" -- a concrete, quantified
                # transmission signal, not just a significant event) from
                # verification._classify_direct_news. Every other path (regulatory
                # documents, supply-chain/material matches) is unaffected -- those
                # don't carry a classification_tier field and keep their existing,
                # unweakened behavior exactly as before.
                if m.relationship == "direct" and doc.get("source") == "news":
                    is_confirmed = verdict.get("classification_tier") == 5
                else:
                    # Hard verification gate: classification label alone is NOT
                    # sufficient -- `mechanism` is a structured field the verifier
                    # itself must populate (see `verification.classify_match`), never
                    # inferred by scanning the free-text recommendation for
                    # disclaimer phrases ("no established connection" etc.), which a
                    # reworded response could trivially evade. Confirmed live: a
                    # classification-only gate let "evidence_supported_hypothesis"
                    # through on bare coincidental word overlap (the "Compensation
                    # Programs" / OWCP boilerplate case) with no real mechanism ever
                    # stated anywhere in the structured verdict.
                    is_confirmed = (
                        classification in _ALERT_WORTHY_CLASSIFICATIONS
                        and bool(verdict.get("mechanism"))
                    )
                try:
                    rec_text = _generate_recommendation(
                        client,
                        document_title=doc.get("title", ""),
                        match=m,
                        industry=industries.get(m.symbol),
                        classification=classification,
                        price_note=_cached_price_note(m.symbol),
                        persona=persona,
                    )
                except Exception as exc:
                    rec_text = None
                    rec_error = f"{type(exc).__name__}: {exc}"
                else:
                    rec_error = None
                recommendations.append(
                    {
                        "symbol": m.symbol,
                        "relationship": m.relationship,
                        "matched_entity": m.matched_entity,
                        "evidence_snippet": m.evidence_snippet,
                        "classification": classification,
                        "classification_tier": verdict.get("classification_tier"),
                        "exposure_mechanism": verdict.get("mechanism"),
                        "verification_reasoning": verdict.get("reasoning"),
                        "is_confirmed_alert": is_confirmed,
                        "recommendation": rec_text,
                        "recommendation_error": rec_error,
                    }
                )

            if not recommendations:
                continue  # everything found was dismissed in Stage 2

            alerts.append(
                {
                    "user_id": user_id,
                    "document_number": doc.get("document_number"),
                    "title": doc.get("title"),
                    "publication_date": doc.get("publication_date"),
                    "document_url": doc.get("document_url"),
                    "matches": recommendations,
                }
            )
    return alerts
