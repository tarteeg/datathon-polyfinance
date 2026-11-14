"""New, general-purpose research tools for the Ripple Investigation Agent (see
docs/RIPPLE_INVESTIGATION.md). Unlike the rest of the tool layer, these are not
scoped to any fixed company/material list -- they let an investigation ask a new
question ("does anyone mention X?") instead of only checking against a closed seed
list (KNOWN_SUPPLIER_ALIASES, KNOWN_COMPANY_NAMES).

Nothing here invents a relationship. `search_filings_fulltext` only ever reports a
literal textual match with its exact evidence sentence, same discipline as
`graph.company_graph.extract_supplier_edges_from_filing_text`. `propose_candidate_entities`
is explicitly a noisy heuristic (regex proper-noun extraction, not NER) that produces
*candidates to investigate further*, never a claim -- every candidate must still be
re-checked by search_filings_fulltext (or the existing alerts/relevance.py path)
before it can be labeled anything above "unverified possibility".
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from strands import tool

from app.riskripple.config import FIXTURES_DIR
from app.riskripple.ingestion import filings_sec

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# All symbols with a 10-K text fixture available. Hardcoded to the 3 companies the
# demo fixture set actually has filings for (see data/fixtures/filings/) -- this is a
# fixture-availability limit, not an industry assumption; a real deployment would list
# the filings/ prefix in S3 instead of a fixed tuple.
_ALL_FIXTURE_FILING_SYMBOLS = ("NVDA", "AMD", "INTC")

_CONNECTOR_WORDS = {"of", "and", "for", "the", "in", "on", "a", "an"}
_LEADING_NOISE_WORDS = {"Ltd", "And", "Or", "The", "This", "These", "It", "We", "Our"}
# Maximally-common phrases with no differentiating signal: every U.S. regulatory
# document and every U.S. company's 10-K says "United States" constantly, including in
# machine-generated XBRL boilerplate -- a literal match on this tells an investigation
# nothing. Confirmed by actually running the loop against real data: this exact phrase
# produced a junk "evidence_supported_hypothesis" sourced from raw XBRL tag soup, not
# prose, in all 3 fixture filings simultaneously (a match on every single filing is
# itself a sign of boilerplate, not a real signal). Small, explicit denylist -- same
# philosophy as KNOWN_SUPPLIER_ALIASES: curated, not a general informativeness model.
_GENERIC_NOISE_CANDIDATES = {"united states", "u.s.", "united states of america"}
_CANDIDATE_ENTITY_RE = re.compile(
    r"\b[A-Z][A-Za-z&.\-]*(?:\s+(?:[A-Z][A-Za-z&.\-]*|of|and|for|the|in|on))*\b"
)

# Single-word candidates: materials, technologies, and sanctions-relevant
# geography/trade terms an event description names that the proper-noun regex above
# structurally cannot catch (it only matches capitalized multi-word phrases).
# Confirmed by direct test: feeding the regex-only extractor a real sanctions-event
# sentence mentioning "titanium", "Russia", and "semiconductors" returned only
# ['Following the Russia-Ukraine', 'United States and Canada'] -- it missed every
# single-word term.
#
# An earlier version of this tried "any word >= 4 chars, minus a stopword list" --
# confirmed BROKEN by a real end-to-end alert-scan run: common English words like
# "Rules", "Management", "Control", "Entity", "sets", "announces", "Administration"
# each coincidentally appear SOMEWHERE in any sufficiently long (~500KB) real filing
# purely by chance, regardless of actual relevance, producing a 100% false-positive
# alert rate across every portfolio tested. A frequency filter against the available
# fixture corpus didn't fully fix it either (a word doesn't need to appear in most
# filings to be a false positive from a single lucky hit). A stopword DENYLIST can
# never keep up with the much larger space of generic English words that will
# spuriously match -- so this uses a curated ALLOWLIST instead, same philosophy as
# KNOWN_SUPPLIER_ALIASES: specific, extensible, honest about covering known
# categories (materials/commodities, sanctions-relevant geography, trade/tech terms)
# rather than claiming general entity recognition. A term outside this list still
# gets a chance via the capitalized multi-word phrase path above, or via the agent's
# own `search_filings_fulltext`/`search_sec_edgar_live` tool calls, which aren't
# constrained to this list.
_SINGLE_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")
_SINGLE_WORD_ALLOWLIST = frozenset({
    # Materials / commodities / strategic minerals
    "titanium", "copper", "cobalt", "lithium", "nickel", "aluminum", "aluminium",
    "steel", "uranium", "tungsten", "palladium", "platinum", "silicon", "gallium",
    "germanium", "neodymium", "graphite", "magnesium", "rhodium", "silver", "gold",
    "oil", "gas", "wheat", "grain",
    # Technology / product categories frequently the subject of export controls
    "semiconductor", "semiconductors", "chip", "chips", "wafer", "wafers",
    "microchip", "microchips", "software", "hardware", "encryption", "satellite",
    "satellites", "drone", "drones", "battery", "batteries",
    # Sanctions / trade mechanism terms
    "sanctions", "sanctioned", "embargo", "embargoes", "tariff", "tariffs",
    "blacklist", "blacklisted",
    # Countries/nationalities most commonly the subject of U.S./Canadian sanctions
    # and export-control regimes (not an exhaustive geopolitical list -- a curated
    # set matching this system's actual demo scenarios).
    "russia", "russian", "ukraine", "ukrainian", "china", "chinese", "iran",
    "iranian", "cuba", "cuban", "syria", "syrian", "venezuela", "venezuelan",
    "belarus", "belarusian", "myanmar", "taiwan", "taiwanese", "korea", "korean",
})


def _single_word_candidates(text: str, max_candidates: int) -> list[str]:
    seen: dict[str, None] = {}
    for raw_match in _SINGLE_WORD_RE.finditer(text):
        word = raw_match.group(0)
        if word.lower() not in _SINGLE_WORD_ALLOWLIST:
            continue
        # Keep the term as it actually appears (preserves case for proper nouns like
        # "Russia"; lowercase common nouns like "titanium" stay lowercase) -- the
        # downstream match is case-insensitive anyway, this is just for readability.
        seen.setdefault(word, None)
        if len(seen) >= max_candidates:
            break
    return list(seen.keys())


def _word_match(alias: str, text: str) -> re.Match | None:
    return re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE)


def _sentence_containing(text: str, match: re.Match) -> str:
    for paragraph in text.split("\n\n"):
        if match.group(0).lower() not in paragraph.lower():
            continue
        for sentence in _SENTENCE_SPLIT_RE.split(paragraph):
            if match.group(0).lower() in sentence.lower():
                return sentence.strip()
    return text[max(0, match.start() - 80) : match.end() + 80].strip()


@tool
def search_filings_fulltext(query: str, symbols: list[str] | None = None, fixtures_dir: str | None = None) -> dict:
    """Search ALL available company 10-K fixtures (or just `symbols`, if given) for a
    literal, word-boundary, case-insensitive match of `query` -- e.g. a material, a
    technology, or an entity name not in any existing seed list. Returns one entry per
    company where a match was found, each with the exact evidence sentence, so a
    caller can investigate a brand-new term the same way the existing supplier-edge
    extraction investigates a known one.
    """
    base = Path(fixtures_dir or FIXTURES_DIR) / "filings"
    symbols = symbols or list(_ALL_FIXTURE_FILING_SYMBOLS)

    hits = []
    for symbol in symbols:
        text_path = base / f"{symbol}_10K.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text()
        match = _word_match(query, text)
        if match:
            hits.append({"symbol": symbol, "matched_text": match.group(0), "evidence_snippet": _sentence_containing(text, match)})

    return {"query": query, "symbols_searched": symbols, "hits": hits, "found": len(hits) > 0}


def extract_candidate_entities(text: str, max_candidates: int = 10) -> list[str]:
    """Plain (non-@tool) implementation shared by `propose_candidate_entities` below
    and by `exposure_tools.load_company_graph`, which needs to run this same
    extraction internally (not as an agent-invoked tool call) to build a per-event,
    per-portfolio exposure graph instead of only checking the fixed
    KNOWN_SUPPLIER_ALIASES seed list."""
    seen: dict[str, None] = {}
    for raw_match in _CANDIDATE_ENTITY_RE.finditer(text):
        candidate = raw_match.group(0).strip()
        tokens = candidate.split()
        if len(tokens) < 2 or len(candidate) < 6:
            continue
        if tokens[0] in _LEADING_NOISE_WORDS:
            continue
        if candidate.lower() in _GENERIC_NOISE_CANDIDATES:
            continue
        non_connector_tokens = [t for t in tokens if t.lower() not in _CONNECTOR_WORDS]
        if len(non_connector_tokens) < 2:
            continue
        seen.setdefault(candidate, None)

    phrase_candidates = list(seen.keys())
    remaining = max(0, max_candidates - len(phrase_candidates))
    single_word = _single_word_candidates(text, remaining) if remaining else []
    return (phrase_candidates + single_word)[:max_candidates]


@tool
def propose_candidate_entities(text: str, max_candidates: int = 10) -> dict:
    """Heuristically propose candidate entity/organization names from free text (a
    regulatory document's title+abstract, a news snippet) for further investigation.

    This is NOT named-entity recognition and NOT a claim of any kind -- it's a regex
    proper-noun-phrase extractor, intentionally noisy. Every candidate it returns must
    still be verified (e.g. via search_filings_fulltext or alerts.relevance) before
    being treated as more than "worth checking."
    """
    candidates = extract_candidate_entities(text, max_candidates=max_candidates)
    return {"candidates": candidates, "method": "regex proper-noun extraction (heuristic, not NER)"}


@tool
def search_sec_edgar_live(query: str, entity_name: str | None = None, forms: str = "10-K") -> dict:
    """Live SEC EDGAR full-text search across ALL real public filings (not just the
    3 companies in the local fixture set) -- use this when a candidate entity or
    material isn't found by search_filings_fulltext, before concluding there's no
    evidence anywhere. Fetches the top real hit's filing text and returns the actual
    sentence containing the query as evidence, same discipline as every other tool
    here: a literal match with its real source sentence, or found=False, never a
    guess. Requires network access -- will raise if offline (no silent fallback that
    could be mistaken for a real "not found" result).

    Defaults to the last 3 years: an unscoped EDGAR full-text search ranks by
    relevance score, which can surface a real but stale match ahead of a current one
    -- confirmed live: an unscoped "copper"+Intel search returned a 2001 filing about
    Ethernet cabling, not a current supply-chain disclosure. Current portfolio risk
    calls for current disclosures.

    On a network/parsing failure, returns {"found": False, "error": "..."} rather
    than letting an exception (or a multi-megabyte traceback, since the underlying
    filing fetch can be several MB) propagate into the agent's tool-result stream --
    confirmed necessary: an earlier bug here (a missing import) surfaced as repeated
    opaque failures during a live agent run before being caught and fixed. This is
    still a real, distinguishable failure signal (the "error" key), not a silent
    false negative.
    """
    try:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=365 * 3)
        result = filings_sec.search_filings_fulltext(
            query, entity_name=entity_name, forms=forms,
            start_date=start.isoformat(), end_date=end.isoformat(), limit=3,
        )
        if not result.hits:
            return {"query": query, "found": False, "hits": []}

        top = result.hits[0]
        text, _ = filings_sec.fetch_filing_text(
            top.cik,
            filings_sec.FilingSummary(
                accession_number=top.accession_number,
                form_type=top.form_type,
                filing_date=top.filing_date,
                report_date="",
                primary_document=top.primary_document,
            ),
            max_chars=50_000,
        )
        match = _word_match(query, text)
        evidence_snippet = _sentence_containing(text, match) if match else ""
    except Exception as e:
        return {"query": query, "found": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    return {
        "query": query,
        "found": True,
        "entity_name": top.entity_name,
        "form_type": top.form_type,
        "filing_date": top.filing_date,
        "document_url": top.document_url,
        "evidence_snippet": evidence_snippet,
        "other_hits": [h.entity_name for h in result.hits[1:]],
    }


ALL_RESEARCH_TOOLS = [
    search_filings_fulltext,
    propose_candidate_entities,
    search_sec_edgar_live,
]
