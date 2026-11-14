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

from app.riskripple.alerts.relevance import RelevanceMatch, check_relevance
from app.riskripple.tools.exposure_tools import load_company_graph

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))

RECOMMENDATION_SYSTEM_PROMPT = """You are RiskRipple AI's alert-recommendation writer.
You are given: a regulatory/sanctions document, a specific real portfolio holding it
has been matched to (directly or via a real, evidence-based supply-chain/material
link), and the exact evidence snippet that justified the match. Write a 2-3 sentence
recommendation for the portfolio holder.

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
  say so explicitly; do not overstate certainty."""


def _generate_recommendation(
    client, *, document_title: str, match: RelevanceMatch, industry: str | None
) -> str:
    relationship_note = (
        "a direct mention of this holding" if match.relationship == "direct"
        else f"an indirect supply-chain/material link via '{match.node_id}'"
    )
    user_text = (
        f"Document: {document_title}\n"
        f"Portfolio holding: {match.symbol}"
        + (f" (SEC industry: {industry})" if industry else "")
        + f"\nMatch type: {relationship_note}\n"
        f"Evidence snippet actually found: \"{match.evidence_snippet}\"\n\n"
        "Write the recommendation now."
    )
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": RECOMMENDATION_SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.2},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def run_alert_scan(
    *,
    documents: list[dict],
    portfolios: dict[str, list[str]],
    bedrock_client=None,
) -> list[dict]:
    """`documents` is a list of {"document_number", "title", "abstract", ...} (the
    shape `ingestion.regulatory_events.search_documents*` returns, as plain dicts).
    `portfolios` is {user_id: [ticker, ...]}, as `alerts.db.get_all_portfolios`
    returns.

    Returns one entry per (user, document) pair that was found genuinely relevant,
    each with its real relevance matches and a generated recommendation. Does NOT
    persist anything or track "seen" documents across calls (unlike riskripple-ai's
    DynamoDB-backed version) -- this repo has no alerts table yet, and this endpoint
    is meant to be called with a specific, already-fetched/deduplicated document set
    by its caller rather than silently maintaining hidden state in a hackathon demo.
    A persisted "seen documents" table is a reasonable next step, not implemented
    here given the time available.
    """
    client = bedrock_client or boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

    alerts: list[dict] = []
    # Build each portfolio's exposure graph once per document (not once per portfolio
    # total), since the graph is event_description-specific -- it must be rebuilt
    # per document, but is naturally reused across nothing else here.
    for doc in documents:
        doc_text = f"{doc.get('title', '')}\n\n{doc.get('abstract') or ''}"
        for user_id, symbols in portfolios.items():
            if not symbols:
                continue
            graph_json = load_company_graph(portfolio_symbols=symbols, event_description=doc_text)
            matches = check_relevance(doc_text, graph_json, symbols)
            if not matches:
                continue  # genuinely not relevant to this user's holdings -- correctly suppressed

            industries = graph_json.get("industries", {})
            recommendations = []
            for m in matches:
                try:
                    rec_text = _generate_recommendation(
                        client, document_title=doc.get("title", ""), match=m, industry=industries.get(m.symbol)
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
                        "recommendation": rec_text,
                        "recommendation_error": rec_error,
                    }
                )

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
