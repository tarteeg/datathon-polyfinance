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

# A news article directly naming a held company is NOT automatically a flaggable
# event the way a regulatory document naming a company is -- a government filing
# rarely namedrops a company incidentally, but ordinary news routinely does (earnings
# coverage, analyst notes, a generic "stock moved today" piece) without describing
# anything a holder would want to be alerted to. This is the real gap broadening the
# news feed (removing the old keyword pre-filter) would otherwise reopen: without
# this check, every single article about a held ticker would hit the "direct match"
# path and become an automatic verified_fact alert. This prompt makes that judgment
# per article instead, using the same fact-grading discipline as everywhere else in
# this codebase.
DIRECT_NEWS_VERIFICATION_SYSTEM_PROMPT = """You are RiskRipple AI's news materiality
classifier. You are given a real news article that is directly about a company the
user holds (the company's name or ticker appears in the article). Decide whether this
article describes something a reasonably attentive investor would want a dedicated
alert for -- a leadership change, a legal action or investigation, a regulatory
action, a significant recall or safety issue, a major operational disruption (a
cyberattack, a plant closure, a controversy) -- versus routine market/analyst
commentary that doesn't rise to a distinct flaggable event (an earnings beat/miss
without further detail, a price-target change, a generic "stock moved X%" article, a
minor analyst note).

Respond with exactly one JSON object and nothing else:
{"classification": "...", "reasoning": "..."}

classification must be exactly one of:
- "verified_fact": the article explicitly and specifically describes a notable,
  concrete event about this company (names a specific executive change, a specific
  lawsuit/investigation, a specific recall, a specific major disruption).
- "evidence_supported_hypothesis": the article describes something plausibly notable
  but with limited specifics or an uncertain outcome.
- "unverified_possibility": the article gestures at something potentially significant
  but lacks enough concrete detail to say more.
- "dismissed_insufficient_evidence": routine market commentary, earnings/analyst
  coverage, or generic stock-movement reporting with no distinct event -- not worth a
  dedicated alert.
Do not classify an ordinary earnings beat/miss, an analyst price-target change, or a
generic "stock rose/fell" article as anything other than dismissed_insufficient_evidence."""


def _classify_direct_news(client, *, document_title: str, document_text: str, symbol: str) -> dict:
    user_text = (
        f"Article title: {document_title}\n"
        f"Portfolio holding this article is directly about: {symbol}\n"
        f"Article text: \"{document_text[:4000]}\"\n\n"
        "Classify now."
    )
    try:
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": DIRECT_NEWS_VERIFICATION_SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            inferenceConfig={"maxTokens": 150, "temperature": 0.0},
        )
        raw = response["output"]["message"]["content"][0]["text"].strip()
        raw = raw.strip("`").strip()
        if raw[:4].lower() == "json":
            raw = raw[4:].strip()
        parsed = json.loads(raw)
        classification = parsed.get("classification")
        if classification not in VALID_CLASSIFICATIONS:
            classification = "unverified_possibility"
        return {"classification": classification, "reasoning": parsed.get("reasoning", "")}
    except Exception as exc:
        # Fail closed: an article this check couldn't classify must never silently
        # become a confirmed alert.
        return {
            "classification": "unverified_possibility",
            "reasoning": f"Direct-news verification call failed ({type(exc).__name__}); treated as unverified rather than fabricating a decision.",
        }


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
    document_source: str = "regulatory",
    document_text: str | None = None,
) -> dict:
    """Returns {"classification": ..., "reasoning": ...}. `client` is a
    `boto3.client("bedrock-runtime", ...)`, only ever invoked for a match flagged
    `needs_verification=True` that also fails the free heuristic check below, or for
    a "direct" match on a `document_source="news"` document (see
    `_classify_direct_news`).

    `document_source` distinguishes a regulatory/government filing (where a document
    directly naming a company is itself inherently significant -- these don't
    namedrop companies incidentally) from a news article (where a direct mention is
    routine and needs its own materiality judgment, not an automatic pass).
    """
    if match.relationship == "direct":
        if document_source == "news":
            return _classify_direct_news(
                client, document_title=document_title, document_text=document_text or "", symbol=match.symbol
            )
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
