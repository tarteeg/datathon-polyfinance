"""Structured recording tools for the Ripple Investigator agent to call at the end of
its investigation. These exist so the backend can extract machine-readable decisions
(which exposure tier applies to each holding; what the one bounded follow-up question
found) from the agent's real tool-call trace, instead of parsing free text out of its
prose answer. The agent still DECIDES the tier/classification from its own evidence --
these tools only constrain the vocabulary it can use to report that decision, the same
"LLM picks the key, fixed code picks any number" split used throughout this codebase
(see finance/stress.py's TIER_SHOCKS).
"""
from __future__ import annotations

from strands import tool

EXPOSURE_TIERS = ("direct_verified", "indirect_evidence_supported", "unverified_possibility", "no_established_link")
FOLLOWUP_CLASSIFICATIONS = ("supported", "unsupported", "unresolved")


@tool
def record_exposure_classification(symbol: str, tier: str, reason: str) -> dict:
    """Record your final exposure-tier classification for one portfolio holding.
    `tier` MUST be exactly one of: direct_verified (the event or a verified_fact
    names this holding/its business directly), indirect_evidence_supported (a real,
    evidence-supported hypothesis connects this holding to the event),
    unverified_possibility (plausible but no real supporting evidence found), or
    no_established_link (no direct link found in the evidence searched -- this does
    NOT mean the holding definitely has zero real-world exposure, only that this
    investigation's search didn't find one; say so in `reason` if the holding's
    industry wasn't well covered by the tools you had). Call this exactly once per
    holding you were asked to investigate, after you've finished gathering evidence
    for it. This tool does not compute anything -- it only records your classification
    so it can be shown to the user and used in the portfolio-impact calculation.
    """
    if tier not in EXPOSURE_TIERS:
        return {"recorded": False, "error": f"tier must be one of {EXPOSURE_TIERS}, got {tier!r}"}
    return {"recorded": True, "symbol": symbol, "tier": tier, "reason": reason}


@tool
def record_followup_finding(
    question: str,
    tool_used: str,
    classification: str,
    summary: str,
    discovered_entity: str | None = None,
    discovered_ticker: str | None = None,
    discovery_relevance: str | None = None,
) -> dict:
    """Record the result of your ONE bounded autonomous follow-up question. After
    completing the main investigation, generate exactly one additional question about
    a downstream relationship or exposure channel you have NOT already covered
    (e.g. a supplier-of-a-supplier, a competitor, a major customer, a macro
    transmission channel) -- pick whichever is actually most relevant given what
    you've already found, do not use a fixed/generic question. Use exactly one more
    tool call to investigate it, then call this tool once with: `question` (what you
    asked), `tool_used` (which tool you called to investigate it), `classification`
    (MUST be exactly one of: supported, unsupported, unresolved), and `summary` (what
    you actually found, in 1-3 sentences, grounded in that tool's real result -- never
    invent a finding to make the follow-up look more conclusive than it was). Call
    this at most once per investigation.

    If that one follow-up question happens to surface a real company, person, or other
    entity that is NOT already in the portfolio you were given and was NOT named by
    the user's event description -- found via a real tool result, e.g. a supplier,
    competitor, or affected producer/importer turned up by search_sec_edgar_live or
    propose_candidate_entities -- name it explicitly via `discovered_entity` (its name)
    and, if known, `discovered_ticker` (its ticker; leave as None if you don't have a
    reliable ticker for it, e.g. a private company, a country, or a person), plus
    `discovery_relevance` (1-2 sentences on why it matters here, grounded in the same
    real tool result, never invented). The portfolio is the destination of this
    investigation, not the boundary of what you're allowed to notice -- but only fill
    these fields when your one follow-up question actually surfaced something real;
    leave all three as None if it didn't, rather than forcing a discovery that isn't
    there.
    """
    if classification not in FOLLOWUP_CLASSIFICATIONS:
        return {"recorded": False, "error": f"classification must be one of {FOLLOWUP_CLASSIFICATIONS}, got {classification!r}"}
    return {
        "recorded": True,
        "question": question,
        "tool_used": tool_used,
        "classification": classification,
        "summary": summary,
        "discovered_entity": discovered_entity,
        "discovered_ticker": discovered_ticker,
        "discovery_relevance": discovery_relevance,
    }


ALL_PORTFOLIO_TOOLS = [record_exposure_classification, record_followup_finding]
