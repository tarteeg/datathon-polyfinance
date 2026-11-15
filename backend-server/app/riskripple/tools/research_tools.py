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

_CONNECTOR_WORDS = {"of", "and", "for", "the", "in", "on", "a", "an", "to"}
_LEADING_NOISE_WORDS = {"Ltd", "And", "Or", "The", "This", "These", "It", "We", "Our"}

# Confirmed by a real live alert-scan run against the full Federal Register default
# document set (not just a small sample): the capitalized-multi-word-phrase regex
# below produces phrases like "Federal Register", "Executive Order", "Entity List",
# "Performance Standards", and "Unified Agenda" -- these are capitalized multi-word
# phrases, so they pass every existing filter, but they describe the REGULATORY
# PROCESS ITSELF (how a rule gets published/ordered/listed/measured/scheduled), not
# any specific material, technology, company, or geography. "Federal Register" in
# particular appears in nearly every regulatory document (it's the publication's own
# name) and in generic compliance boilerplate in nearly every 10-K, so it produced a
# real false-positive alert pairing a Horse Protection Act rule with NVDA, and a
# generic annual rulemaking index ("Unified Agenda") with both AAPL and NVDA.
#
# A per-document corpus-frequency filter (exposure_tools._filter_boilerplate_candidates)
# doesn't catch this reliably: with a small fixture corpus, a generic procedural
# phrase doesn't need to hit 75% of filings to be meaningless -- it only needs to hit
# ONE unrelated filing's boilerplate once to produce a false alert. This is a semantic
# property of the phrase itself (it's about rulemaking machinery, not substance), not
# a frequency property, so it's filtered here unconditionally rather than relying on
# which fixtures happen to be in the corpus at query time.
#
# Rule: if EVERY significant (non-connector) word in a multi-word candidate is drawn
# from this administrative/procedural vocabulary, the candidate is dropped regardless
# of corpus frequency. A phrase with at least one word outside this set (a real
# material, country, company, or named act like "Uyghur Forced Labor Prevention Act")
# survives even if it also contains generic words like "Act".
_GENERIC_PROCEDURAL_WORDS = {
    # NOTE: "entity"/"list" are deliberately excluded even though "Entity List"
    # looks like the same class of phrase as "Federal Register" -- it isn't. The
    # U.S. Commerce Department's "Entity List" is a real, specific export-control
    # mechanism that semiconductor companies substantively disclose real exposure
    # to (confirmed: AMD's actual 10-K describes its THATIC joint venture being
    # directly added to it; NVDA's actual 10-K discusses export licensing exposure
    # tied to the U.S. Entity List). Denylisting "entity"/"list" caused a real
    # regression -- it silently dropped that genuine match. "Federal Register" and
    # "Executive Order", by contrast, only ever describe the publishing/ordering
    # mechanism of a rule, never a specific list, company, or restriction with its
    # own substantive consequences -- that's the actual distinguishing property,
    # not "sounds bureaucratic."
    "federal", "register", "executive", "order", "orders",
    "performance", "standards", "standard", "unified", "agenda",
    "regulatory", "deregulatory", "flexibility", "act", "acts", "rule", "rules",
    "notice", "notices", "regarding", "final", "interim", "proposed", "advance",
    "comment", "comments", "administration", "administrative", "department",
    "office", "bureau", "commission", "agency", "agencies", "program", "programs",
    "access", "support", "supporting", "restoring", "introduction", "title",
    "chapter", "section", "part", "subpart", "docket", "procedure", "procedures",
    "guidance", "framework", "initiative", "action", "actions", "plan", "plans",
    "review", "update", "updates", "request", "requirements", "requirement",
    "information", "collection", "extension", "amendment", "amendments",
    # Confirmed live: "Privacy Act of 1974; Matching Program" survived this filter
    # (not every word was denylisted) and was promoted to a confirmed alert for both
    # NVDA and AMD with zero real connection -- same class of bug as "Federal
    # Register"/"Executive Order", a generic administrative-mechanism phrase, not a
    # specific list/restriction with real consequences.
    "privacy", "matching", "system", "systems", "record", "records", "data",
}


def _is_generic_procedural_phrase(candidate: str) -> bool:
    # Confirmed live: "Privacy Act of 1974; Matching Program" survived this check
    # despite every real word being denylisted, because bare .split() left trailing
    # punctuation on "1974;" -- a token that's neither a connector nor in the
    # denylist, so "all tokens denylisted" failed on a stray punctuation artifact,
    # not a real word. Strip non-alphanumeric characters per token, and skip
    # pure-digit tokens (a bare year/section number adds no specificity by itself)
    # the same way connector words are skipped.
    raw_tokens = [re.sub(r"[^\w]", "", t).lower() for t in candidate.split()]
    tokens = [t for t in raw_tokens if t and t not in _CONNECTOR_WORDS and not t.isdigit()]
    return bool(tokens) and all(t in _GENERIC_PROCEDURAL_WORDS for t in tokens)
# Maximally-common phrases with no differentiating signal: every U.S. regulatory
# document and every U.S. company's 10-K says "United States" constantly, including in
# machine-generated XBRL boilerplate -- a literal match on this tells an investigation
# nothing. Confirmed by actually running the loop against real data: this exact phrase
# produced a junk "evidence_supported_hypothesis" sourced from raw XBRL tag soup, not
# prose, in all 3 fixture filings simultaneously (a match on every single filing is
# itself a sign of boilerplate, not a real signal). Small, explicit denylist -- same
# philosophy as KNOWN_SUPPLIER_ALIASES: curated, not a general informativeness model.
_GENERIC_NOISE_CANDIDATES = {"united states", "u.s.", "united states of america"}

# Confirmed by a real live scoped alert scan: "Federal Communications Commission"
# survived `_is_generic_procedural_phrase` (because "communications" isn't in that
# word list) and was treated as a "specific term", firing a confirmed alert pairing
# an FCC radio-altimeter spectrum rule with TTWO (Take-Two Interactive, a video game
# publisher) -- a video-game company's 10-K almost certainly mentions the FCC
# somewhere in generic boilerplate (e.g. device/broadcast compliance disclosures),
# which tells an investigation nothing about THIS specific rule. Same failure shape
# as "Federal Register": a regulatory body's own NAME is invoked in near-universal
# compliance boilerplate across virtually every public company, so a bare agency-name
# match is not real discriminating evidence on its own -- unlike a substantive,
# narrative connection to that agency (e.g. Intel's actual CHIPS Act / Department of
# Commerce equity relationship, which the full /investigate agent can still find via
# its own deep full-text reads; this denylist only blocks the fast, cheap
# candidate-matching path a scan uses, not the agent's own reasoning). Curated by
# full name (not composition rules) because agency identities are a small, stable,
# enumerable set, not a general vocabulary to approximate.
_GENERIC_AGENCY_NAMES = {
    "federal communications commission", "securities and exchange commission",
    "environmental protection agency", "food and drug administration",
    "federal trade commission", "internal revenue service",
    "department of justice", "department of labor", "department of the treasury",
    "department of energy", "department of transportation",
    "federal aviation administration", "federal reserve",
    "federal deposit insurance corporation", "department of commerce",
    "consumer financial protection bureau", "occupational safety and health administration",
}
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

# SPECIFIC terms: a literal match on one of these is itself meaningful evidence --
# a company's filing doesn't generically mention "titanium" the way it generically
# mentions "semiconductor" or "China". Confirmed by this session's own testing: a
# company naming a specific material is rare and substantive (e.g. Boeing's 10-K
# naming titanium as a named critical raw material), unlike generic category words
# which show up in nearly any company's filing in that broad industry regardless of
# real relevance to a specific event.
_SPECIFIC_SINGLE_WORD_TERMS = frozenset({
    "titanium", "copper", "cobalt", "lithium", "nickel", "aluminum", "aluminium",
    "steel", "uranium", "tungsten", "palladium", "platinum", "silicon", "gallium",
    "germanium", "neodymium", "graphite", "magnesium", "rhodium", "silver", "gold",
    "oil", "gas", "wheat", "grain",
})

# GENERIC category/mechanism/geography terms: confirmed by a real live alert-scan
# producing a false positive -- an AMD-focused market-roundup article containing the
# word "Semiconductor" fired an alert against AAPL purely because AAPL's own 10-K
# also mentions "semiconductor" somewhere generically. These terms describe a TYPE
# of thing or a TYPE of mechanism (an industry category, a nationality, a sanctions
# instrument), not a specific fact -- same underlying problem as the
# `_GENERIC_PROCEDURAL_WORDS` denylist above, just a different vocabulary (that one
# is about the rulemaking process; this one is about industry/geography categories).
# A literal match on one of these is kept as a Stage-1 CANDIDATE (for recall -- it
# may still turn into a real alert after Stage-2 verification in
# `alerts/verification.py`), but must never become an alert on its own.
_GENERIC_CATEGORY_TERMS = frozenset({
    # Technology/product categories -- too broad to be specific evidence alone.
    "semiconductor", "semiconductors", "chip", "chips", "wafer", "wafers",
    "microchip", "microchips", "software", "hardware", "encryption", "satellite",
    "satellites", "drone", "drones", "battery", "batteries",
    # Sanctions/trade MECHANISM words -- naming the instrument, not a specific target.
    "sanctions", "sanctioned", "embargo", "embargoes", "tariff", "tariffs",
    "blacklist", "blacklisted",
    # Countries/nationalities -- a shared country name alone is geography, not a
    # transmission mechanism (confirmed: the user's own test case explicitly
    # requires "Taiwan" alone to be insufficient).
    "russia", "russian", "ukraine", "ukrainian", "china", "chinese", "iran",
    "iranian", "cuba", "cuban", "syria", "syrian", "venezuela", "venezuelan",
    "belarus", "belarusian", "myanmar", "taiwan", "taiwanese", "korea", "korean",
})

_SINGLE_WORD_ALLOWLIST = _SPECIFIC_SINGLE_WORD_TERMS | _GENERIC_CATEGORY_TERMS

# Curated false-positive phrases for an allowlisted term that is also part of a
# well-known phrase meaning something unrelated -- confirmed live: a real Airbnb/
# Chesky article mentioning "Silicon Valley" (the place) got "silicon" extracted as
# a candidate and then treated as unverified material evidence for AMD/NVDA, because
# "silicon" is in _SPECIFIC_SINGLE_WORD_TERMS and a specific-term match skips Stage-2
# verification entirely (classify_match treats it as already-real evidence). Same
# minimal, curated-exclusion philosophy as every other denylist in this file: a
# short, explicit list of known false-positive phrases per ambiguous term, not a
# general word-sense disambiguation model. Only covers a term's occurrence when it's
# immediately followed by the disambiguating word -- a genuine standalone mention of
# the material elsewhere in the same text is unaffected.
_AMBIGUOUS_TERM_FALSE_POSITIVE_PHRASES: dict[str, tuple[str, ...]] = {
    "silicon": ("silicon valley",),
}


def is_generic_category_term(word: str) -> bool:
    """True if `word` (any case) is a generic industry/geography/mechanism category
    term rather than a specific material/fact -- see `_GENERIC_CATEGORY_TERMS`."""
    return word.lower() in _GENERIC_CATEGORY_TERMS


def is_false_positive_occurrence(word: str, text: str, start: int, end: int) -> bool:
    """True if this specific occurrence of `word` at `text[start:end]` is actually
    part of a known unrelated phrase (see `_AMBIGUOUS_TERM_FALSE_POSITIVE_PHRASES`),
    not a real mention of the thing `word` otherwise denotes."""
    phrases = _AMBIGUOUS_TERM_FALSE_POSITIVE_PHRASES.get(word.lower())
    if not phrases:
        return False
    window = text[start : end + 20].lower()
    return any(window.startswith(phrase) for phrase in phrases)


def _single_word_candidates(text: str, max_candidates: int) -> list[str]:
    seen: dict[str, None] = {}
    for raw_match in _SINGLE_WORD_RE.finditer(text):
        word = raw_match.group(0)
        if word.lower() not in _SINGLE_WORD_ALLOWLIST:
            continue
        if is_false_positive_occurrence(word, text, raw_match.start(), raw_match.end()):
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


def extract_candidate_entities(text: str, max_candidates: int = 10, *, include_phrases: bool = True) -> list[str]:
    """Plain (non-@tool) implementation shared by `propose_candidate_entities` below
    and by `exposure_tools.load_company_graph`, which needs to run this same
    extraction internally (not as an agent-invoked tool call) to build a per-event,
    per-portfolio exposure graph instead of only checking the fixed
    KNOWN_SUPPLIER_ALIASES seed list.

    `include_phrases=False` skips the capitalized-multi-word-phrase path entirely,
    keeping only the curated single-word materials/tech/sanctions-geography
    allowlist. Confirmed necessary for news specifically (not regulatory documents):
    a real news article mentioning "Nvidia Corp" or "Samsung" in passing (a roundup
    of unrelated stock moves, or a company's own competitor-landscape disclosure)
    will literally match that same company's name in ANOTHER held company's 10-K --
    e.g. AMD's real 10-K says "we compete primarily against ... Nvidia Corporation",
    a competitor mention, not a supplier relationship, but
    `extract_supplier_edges_from_filing_text` labels every literal match
    relationship_type="supplier" regardless of context. A Federal Register document
    naming a specific act/list/material is reliably substantive; an arbitrary
    capitalized company name in a news roundup is not. The single-word allowlist
    (titanium, Russia, sanctions, etc.) doesn't have this problem since those terms
    don't double as other portfolio holdings' own competitor names.
    """
    if not include_phrases:
        return _single_word_candidates(text, max_candidates)

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
        if candidate.lower() in _GENERIC_AGENCY_NAMES:
            continue
        non_connector_tokens = [t for t in tokens if t.lower() not in _CONNECTOR_WORDS]
        if len(non_connector_tokens) < 2:
            continue
        if _is_generic_procedural_phrase(candidate):
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
