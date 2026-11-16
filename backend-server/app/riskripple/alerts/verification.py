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
from app.riskripple.tools.research_tools import is_routine_administrative_notice

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

CRITICAL: naming a specific act, program, or agency is NOT by itself sufficient.
"Named something specific" means the evidence states a concrete reason THIS
holding's actual business, products, operations, revenue, or legal exposure would be
affected -- not merely that the holding is "a company" or "a large employer" subject
to some general regulatory or administrative framework. A routine administrative
notice (information collection, paperwork renewal, comment request, claims-processing
procedure) that does not itself describe any company-specific impact is coincidental
overlap, not evidence, even though it names a real act or program by title.

Respond with exactly one JSON object and nothing else:
{"classification": "...", "mechanism": "...", "reasoning": "..."}

classification must be exactly one of:
- "evidence_supported_hypothesis": the evidence given (not your own general
  knowledge) states a concrete reason this SPECIFIC holding's business, products,
  operations, revenue, or legal exposure would plausibly be affected -- a real
  supplier/material/competitor relationship, a named act whose substance (not just
  its title) applies to this holding's actual operations, or an explicit company-
  specific impact.
- "unverified_possibility": a connection is plausible in principle, but the evidence
  given does not establish a concrete, holding-specific reason -- only the shared
  generic word or an administrative/procedural overlap.
- "dismissed_insufficient_evidence": the only real connection is coincidental shared
  use of a generic word or administrative category; no real mechanism is evident
  even as a hypothesis.
Do not choose "evidence_supported_hypothesis" merely because a named act/program/
agency appears, or because the holding is a large company that could in principle be
subject to it -- only when the evidence states a concrete, holding-specific impact.

`mechanism` is a short (<=20 word) plain-language statement of the specific,
holding-specific transmission channel (e.g. "named supplier TSMC manufactures the
holding's chips" or "10-K discloses direct operational exposure to this export
control"), or an empty string if classification is not evidence_supported_hypothesis.
A classification of evidence_supported_hypothesis with an empty mechanism is invalid
-- always state the mechanism when choosing that classification."""

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
#
# Five-level distinction (confirmed live: 3 real Jensen-Huang/NVIDIA leadership-crisis
# stories were reaching `confirmed_alerts` on materiality alone -- "this is a real,
# significant event about a company I hold" was being treated as equivalent to
# "this is evidence-supported portfolio risk exposure," which it is not; a leadership
# story doesn't by itself establish a quantified economic transmission mechanism the
# way a SEC filing's own risk-factor disclosure does):
#   1. article discovered            -> handled upstream, always in `articles`.
#   2. event reported, not material  -> "dismissed_insufficient_evidence" (routine
#                                        noise: an earnings beat, a price-target
#                                        change, a generic "stock moved X%" piece).
#   3/4. event materially significant to the company, with at most a plausible,
#        unquantified mechanism named -> "potential_exposure_unquantified". Levels 3
#        and 4 (no mechanism named vs. a plausible-but-unquantified mechanism named)
#        are deliberately collapsed into one practical bucket here: both land in
#        `investigation_candidates`, never `confirmed_alerts`, so the distinction
#        between them doesn't change any behavior -- only level 5 does.
#   5. evidence-supported portfolio exposure -> "evidence_supported_portfolio_exposure".
#      ONLY this level may become a confirmed alert. Requires the article itself to
#      report a CONCRETE, QUANTIFIED transmission signal tied explicitly to this
#      event -- e.g. a specific stock-price reaction ("shares fell 12% after...")
#      explicitly attributed to this event, or an explicit, specific financial/
#      contractual consequence named in the article (a named dollar impact, a
#      specific contract loss) -- not just "this is newsworthy and could matter."
DIRECT_NEWS_VERIFICATION_SYSTEM_PROMPT = """You are RiskRipple AI's news materiality
and portfolio-exposure classifier. You are given a real news article that is directly
about a company the user holds (the company's name, ticker, or a named executive
appears in the article). Two separate questions matter here, and they are NOT the
same question:
  (a) Is this a real, materially significant event about the company (a leadership
      change, a legal action or investigation, a regulatory action, a significant
      recall or safety issue, a major operational disruption)?
  (b) Does the article itself report a CONCRETE, QUANTIFIED economic transmission
      signal tied explicitly to that event -- a specific stock-price reaction
      ("shares fell 12% following the announcement"), a specific named dollar/
      contract impact, or an explicit connection to a specific disclosed risk factor?

A "yes" to (a) alone is NOT sufficient for the highest classification. A real,
significant leadership crisis is still only a potential, unquantified exposure unless
the article itself names a concrete transmission signal, not just significance.

Respond with exactly one JSON object and nothing else:
{"classification": "...", "mechanism": "...", "reasoning": "..."}

classification must be exactly one of:
- "dismissed_insufficient_evidence": routine market commentary, earnings/analyst
  coverage, or generic stock-movement reporting with no distinct event -- not worth a
  dedicated alert. An ordinary earnings beat/miss, an analyst price-target change, or
  a generic "stock rose/fell" article with no further detail belongs here.
- "potential_exposure_unquantified": a real, materially significant event about this
  company IS described, and a plausible mechanism for portfolio/business impact may
  be inferable (e.g. "leadership instability could affect strategic execution"), but
  the article itself does NOT report a concrete, quantified transmission signal.
  This is the correct answer for most real, significant news -- including a genuine
  leadership crisis -- when the article doesn't go further than reporting the event.
- "evidence_supported_portfolio_exposure": the article itself explicitly reports a
  concrete, quantified transmission signal tied to this specific event (a stated
  stock-price move attributed to it, a named dollar/contract impact, or an explicit
  tie to a specific disclosed risk factor) -- not merely that the event is newsworthy
  or plausibly important.
- "unverified_possibility": genuinely too ambiguous to place in the above.

`mechanism` is a short (<=20 word) plain-language description of the specific
transmission channel you identified (e.g. "leadership instability raising execution
risk" or "explicit 8% share-price drop attributed to this announcement"), or an empty
string if classification is dismissed_insufficient_evidence."""


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
            inferenceConfig={"maxTokens": 200, "temperature": 0.0},
        )
        raw = response["output"]["message"]["content"][0]["text"].strip()
        raw = raw.strip("`").strip()
        if raw[:4].lower() == "json":
            raw = raw[4:].strip()
        parsed = json.loads(raw)
        news_classification = parsed.get("classification")
        if news_classification not in {
            "dismissed_insufficient_evidence",
            "potential_exposure_unquantified",
            "evidence_supported_portfolio_exposure",
            "unverified_possibility",
        }:
            news_classification = "unverified_possibility"
        tier = {
            "dismissed_insufficient_evidence": 2,
            "potential_exposure_unquantified": 4,
            "evidence_supported_portfolio_exposure": 5,
            "unverified_possibility": 3,
        }[news_classification]
        # Map onto the shared VALID_CLASSIFICATIONS vocabulary for backward
        # compatibility with every other caller/display path in this codebase --
        # `classification_tier` is the new field that actually gates confirmation
        # (see pipeline.run_alert_scan), this mapping is for display/reasoning only.
        display_classification = {
            "dismissed_insufficient_evidence": "dismissed_insufficient_evidence",
            "potential_exposure_unquantified": "evidence_supported_hypothesis",
            "evidence_supported_portfolio_exposure": "verified_fact",
            "unverified_possibility": "unverified_possibility",
        }[news_classification]
        return {
            "classification": display_classification,
            "classification_tier": tier,
            "mechanism": parsed.get("mechanism", ""),
            "reasoning": parsed.get("reasoning", ""),
        }
    except Exception as exc:
        # Fail closed: an article this check couldn't classify must never silently
        # become a confirmed alert.
        return {
            "classification": "unverified_possibility",
            "classification_tier": 3,
            "mechanism": "",
            "reasoning": f"Direct-news verification call failed ({type(exc).__name__}); treated as unverified rather than fabricating a decision.",
        }


def _heuristic_classification(match: RelevanceMatch) -> dict | None:
    """Deterministic, free check: does the filing's own evidence snippet ALSO name a
    real, specific entity (a known supplier or a known company name) beyond the bare
    generic term that triggered the match? If so, that is already real, stronger
    evidence -- skip the Bedrock call entirely rather than pay for an LLM opinion
    when a literal fact is already available. Returns a dict with a real, specific
    `mechanism` string (never empty) so this path satisfies the same structured-
    evidence gate as the LLM path -- see `pipeline._ALERT_WORTHY_CLASSIFICATIONS`
    usage, which now requires a non-empty `mechanism` to confirm, not classification
    label alone.
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
            return {
                "classification": "evidence_supported_hypothesis",
                "mechanism": f"Filing evidence names known entity '{name}' alongside '{match.matched_entity}'.",
                "reasoning": "A specific named entity co-occurs with the generic term in the filing evidence (deterministic check, no model call).",
            }
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
    """Returns {"classification": ..., "mechanism": ..., "reasoning": ...}. `client`
    is a `boto3.client("bedrock-runtime", ...)`, only ever invoked for a match
    flagged `needs_verification=True` that also fails the free heuristic check below,
    or for a "direct" match on a `document_source="news"` document (see
    `_classify_direct_news`).

    `mechanism` is the structured evidence field the confirmation gate in
    `alerts.pipeline.run_alert_scan` actually checks -- a classification label alone
    is never sufficient to confirm an alert for a non-direct-news match; a non-empty,
    specific `mechanism` must also be present. This is deliberately a structured
    field produced by the verifier itself, not a phrase-match over generated
    recommendation prose, which a caller could trivially work around by rewording.

    `document_source` distinguishes a regulatory/government filing (where a document
    directly naming a company is itself inherently significant -- these don't
    namedrop companies incidentally) from a news article (where a direct mention is
    routine and needs its own materiality judgment, not an automatic pass). A
    *routine* regulatory notice (see `is_routine_administrative_notice`) is the
    exception: these recur verbatim across thousands of unrelated administrative
    filings, so even a direct mention there doesn't get an automatic pass -- it still
    needs the mechanism check.
    """
    if match.relationship == "direct":
        if document_source == "news":
            return _classify_direct_news(
                client, document_title=document_title, document_text=document_text or "", symbol=match.symbol
            )
        if not is_routine_administrative_notice(document_title):
            return {
                "classification": "verified_fact",
                "mechanism": "Document directly names this holding.",
                "reasoning": "The document directly names this holding.",
            }
        # A routine administrative notice directly naming a company (e.g. as one of
        # many entities in a generic compliance list) isn't inherently significant
        # the way a sanctions order or enforcement action naming a company is --
        # falls through to the shared routine-notice check below, deliberately NOT
        # the `needs_verification` fast path further down (a "direct" match always
        # has needs_verification=False by construction, so it would otherwise hit
        # that fast path and silently undo this downgrade -- confirmed as a real bug
        # during this fix's own verification before the check order was corrected).

    # Checked BEFORE the `needs_verification` fast path below, deliberately --
    # Stage-1's "is this candidate specific" judgment (relevance.RelevanceMatch.
    # needs_verification) is itself just a closed word-list check at extraction time
    # (research_tools._is_generic_procedural_phrase / is_generic_category_term) that
    # can only catch a phrase a human already anticipated. The document-level
    # routine-notice check is an orthogonal, independent signal -- it doesn't depend
    # on recognizing any particular candidate phrase, so it still catches the NEXT
    # never-before-seen bureaucratic phrase from this exact document family even if
    # Stage-1 wrongly calls it "specific." Letting `needs_verification=False` skip
    # this check first was the exact gap that let "Compensation Programs" through
    # originally.
    if is_routine_administrative_notice(document_title):
        heuristic = _heuristic_classification(match)
        if heuristic:
            return heuristic
        # Never worth a Bedrock call -- confirmed live, this exact boilerplate family
        # repeats verbatim across thousands of unrelated notices and has no
        # company-specific content by construction. Kept as an investigation
        # candidate (not confirmed, not dropped) rather than dismissed outright, in
        # case a future notice in this family genuinely does name a holding-specific
        # detail worth a human glance.
        return {
            "classification": "unverified_possibility",
            "mechanism": "",
            "reasoning": "Routine Federal Register/OMB administrative notice (information collection, paperwork renewal, comment request) -- this boilerplate family recurs across unrelated filings regardless of holding, with no company-specific content.",
        }

    if not match.needs_verification:
        return {
            "classification": "evidence_supported_hypothesis",
            "mechanism": f"Literal match on specific term '{match.matched_entity}' (known material/supplier/entity, not a generic category word).",
            "reasoning": f"Literal match on a specific term ('{match.matched_entity}'), not a generic category word.",
        }

    heuristic = _heuristic_classification(match)
    if heuristic:
        return heuristic

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
        mechanism = (parsed.get("mechanism") or "").strip()
        if classification not in VALID_CLASSIFICATIONS or classification == "verified_fact":
            # The model has no basis to claim "direct/verified" from a generic-term
            # match alone -- fail closed to the weaker label rather than trust an
            # out-of-contract response.
            classification = "unverified_possibility"
        if classification == "evidence_supported_hypothesis" and not mechanism:
            # Contract violation: the prompt requires a mechanism whenever this
            # classification is chosen. Fail closed rather than let an empty-
            # mechanism "evidence_supported_hypothesis" slip through the gate on
            # classification label alone.
            classification = "unverified_possibility"
        return {"classification": classification, "mechanism": mechanism, "reasoning": parsed.get("reasoning", "")}
    except Exception as exc:
        # Fail closed: a failed/unparseable verification call must never silently
        # become a confirmed alert -- treat as unverified, not confirmed or dismissed.
        return {
            "classification": "unverified_possibility",
            "mechanism": "",
            "reasoning": f"Verification call failed ({type(exc).__name__}); treated as unverified rather than fabricating a decision.",
        }
