"""Stage 2 of the alert pipeline: before a Stage-1 candidate match becomes a
recorded alert, verify it reflects a real evidence-grounded relationship rather
than coincidental topical word overlap (e.g. a news article and an unrelated
company's 10-K both happening to contain the word "semiconductor" or "Taiwan").

Reuses the exact fact/hypothesis vocabulary this codebase already uses everywhere
else (see `app.riskripple.agents.definitions.RIPPLE_INVESTIGATOR_PROMPT`):
`verified_fact`, `evidence_supported_hypothesis`, `unverified_possibility`. Adds one
new, explicit outcome -- `dismissed_insufficient_evidence` -- for a Stage-1 candidate
that Stage 2 could not support even as a hypothesis.

Classification is cheap by default: a direct match or a match on a SPECIFIC term
(a real material, a known supplier/company name) is classified deterministically,
no Bedrock call. Only a match flagged `needs_verification=True` (generic-category-
only) pays for one single, non-agentic `converse` call -- never a full agent loop,
same cost-conscious discipline as `alerts.pipeline`'s recommendation step.
"""
from __future__ import annotations

import json
import os

from app.riskripple.alerts.relevance import RelevanceMatch

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))

VALID_CLASSIFICATIONS = {
    "verified_fact",
    "evidence_supported_hypothesis",
    "unverified_possibility",
    "dismissed_insufficient_evidence",
}

VERIFICATION_SYSTEM_PROMPT = """You are RiskRipple AI's evidence verifier. You are
given a document (news or regulatory) and a portfolio holding whose ONLY identified
connection to it is a shared generic industry/sector/geography/mechanism word (e.g.
"semiconductor", "Taiwan", "sanctions") -- not a specific named entity, material, or
act. Decide whether a real, specific causal transmission mechanism exists between
this document and this holding, using ONLY the evidence given. Never invent a fact,
source, company name, or mechanism that is not present in the input -- if the
evidence does not name anything specific beyond the generic shared word, say so.

Respond with exactly one JSON object and nothing else:
{"classification": "...", "reasoning": "..."}

classification must be exactly one of:
- "evidence_supported_hypothesis": the evidence given (not your own general
  knowledge) names something specific -- a real supplier, material, named act, or
  company -- that plausibly connects this holding to this document, beyond the bare
  generic word.
- "unverified_possibility": a connection is plausible in principle, but the evidence
  given does not establish anything specific -- only the shared generic word.
- "dismissed_insufficient_evidence": the only real connection is coincidental shared
  use of a generic word; no real mechanism is evident even as a hypothesis.
Do not choose "evidence_supported_hypothesis" merely because the general topic
sounds related -- only when the evidence given names something specific."""


def _heuristic_classification(match: RelevanceMatch) -> str | None:
    """Deterministic, free check: does the filing's own evidence snippet ALSO name a
    real, specific entity (a known supplier or a known company name) beyond the bare
    generic term that triggered the match? If so, that is already real, stronger
    evidence -- skip the Bedrock call entirely rather than pay for an LLM opinion
    when a literal fact is already available.
    """
    from app.riskripple.graph.company_graph import KNOWN_SUPPLIER_ALIASES
    from app.riskripple.tools.exposure_tools import KNOWN_COMPANY_NAMES

    text = match.evidence_snippet.lower()
    matched_lower = match.matched_entity.lower()
    specific_names = list(KNOWN_SUPPLIER_ALIASES.keys()) + list(KNOWN_COMPANY_NAMES.values())
    for alias_list in list(KNOWN_SUPPLIER_ALIASES.values()):
        specific_names.extend(alias_list)
    for name in specific_names:
        if name.lower() != matched_lower and name.lower() in text:
            return "evidence_supported_hypothesis"
    return None


def classify_match(
    client,
    *,
    document_title: str,
    match: RelevanceMatch,
    industry: str | None = None,
) -> dict:
    """Returns {"classification": ..., "reasoning": ...}. `client` is a
    `boto3.client("bedrock-runtime", ...)`, only ever invoked for a match flagged
    `needs_verification=True` that also fails the free heuristic check below.
    """
    if match.relationship == "direct":
        return {"classification": "verified_fact", "reasoning": "The document directly names this holding."}
    if not match.needs_verification:
        return {
            "classification": "evidence_supported_hypothesis",
            "reasoning": f"Literal match on a specific term ('{match.matched_entity}'), not a generic category word.",
        }

    heuristic = _heuristic_classification(match)
    if heuristic:
        return {
            "classification": heuristic,
            "reasoning": "A specific named entity co-occurs with the generic term in the filing evidence (deterministic check, no model call).",
        }

    user_text = (
        f"Document title: {document_title}\n"
        f"Portfolio holding: {match.symbol}" + (f" (SEC industry: {industry})" if industry else "") + "\n"
        f"Shared generic term that triggered this candidate: '{match.matched_entity}'\n"
        f'Filing evidence snippet: "{match.evidence_snippet}"\n\n'
        "Classify now."
    )
    try:
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": VERIFICATION_SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            inferenceConfig={"maxTokens": 200, "temperature": 0.0},
        )
        raw = response["output"]["message"]["content"][0]["text"].strip()
        raw = raw.strip("`").strip()
        if raw[:4].lower() == "json":
            raw = raw[4:].strip()
        parsed = json.loads(raw)
        classification = parsed.get("classification")
        if classification not in VALID_CLASSIFICATIONS or classification == "verified_fact":
            # The model has no basis to claim "direct/verified" from a generic-term
            # match alone -- fail closed to the weaker label rather than trust an
            # out-of-contract response.
            classification = "unverified_possibility"
        return {"classification": classification, "reasoning": parsed.get("reasoning", "")}
    except Exception as exc:
        # Fail closed: a failed/unparseable verification call must never silently
        # become a confirmed alert -- treat as unverified, not confirmed or dismissed.
        return {
            "classification": "unverified_possibility",
            "reasoning": f"Verification call failed ({type(exc).__name__}); treated as unverified rather than fabricating a decision.",
        }
