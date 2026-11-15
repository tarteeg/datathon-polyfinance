"""Agent 3 (Exposure and Contagion Mapper) tool surface."""
from __future__ import annotations

import re

from rapidfuzz import fuzz
from rapidfuzz.utils import default_process
from strands import tool

from app.riskripple.graph.company_graph import (
    KNOWN_SUPPLIER_ALIASES,
    build_graph,
    export_graph_json,
    extract_supplier_edges_from_filing_text,
    find_direct_exposure,
    traverse_relationships,
)
from app.riskripple.config import FIXTURES_DIR
from app.riskripple.ingestion.filings_sec import get_company_title_for_ticker
from app.riskripple.schemas.models import ExposureEdge
from app.riskripple.tools.regulatory_tools import retrieve_company_filings, summarize_event_evidence
from app.riskripple.tools.research_tools import extract_candidate_entities, is_generic_category_term

# Confirmed by a real alert-scan run: broadening candidate extraction to catch single
# words (needed to catch "titanium") also let through generic corporate/regulatory
# boilerplate -- "Management", "Control", "Investment", "Regarding", "Rules" each
# matched literally every one of 8 real filings spanning semiconductors, a utility,
# consumer tech, banking, aerospace, and software, producing a 100% false-positive
# alert rate. Fix: empirically test each candidate against the full available fixture
# corpus (same confirmed-boilerplate methodology already used for "united states" in
# research_tools.py, just applied dynamically instead of to a fixed 3-phrase
# denylist) and drop any candidate that matches almost everything -- a word that is
# "found" in every unrelated company's filing regardless of industry carries no
# signal about this specific event or holding.
_BOILERPLATE_MATCH_THRESHOLD = 0.75

# Multi-word country/region names -- the phrase-level equivalent of
# research_tools._GENERIC_CATEGORY_TERMS' single-word country list ("russia",
# "taiwan", ...). A bare country name alone is geography, not a transmission
# mechanism, whether it's one word or several -- confirmed live: "United Arab
# Emirates" (from a real oil-pipe antidumping case) matched NVDA purely on shared
# geography, no real connection. A closed, enumerable list, not an attempt at general
# phrase classification -- see the caller's comment for why a blanket "any multi-word
# phrase needs verification" rule was tried and reverted (it broke "Entity List").
_GENERIC_GEOGRAPHY_PHRASES = frozenset({
    "United Arab Emirates", "United Kingdom", "South Korea", "North Korea",
    "Saudi Arabia", "South Africa", "New Zealand", "Costa Rica", "Sri Lanka",
    "Hong Kong", "Czech Republic", "Dominican Republic", "El Salvador",
    "Hong Kong SAR", "Taiwan SAR",
})


def _filter_boilerplate_candidates(candidates: dict[str, list[str]], fixtures_dir) -> dict[str, list[str]]:
    import re as _re
    from pathlib import Path as _Path

    base = _Path(fixtures_dir) / "filings" if fixtures_dir else FIXTURES_DIR / "filings"
    corpus_files = list(base.glob("*_10K.txt"))
    if len(corpus_files) < 4:  # too small a corpus to judge "almost everything" meaningfully
        return candidates
    corpus_texts = [p.read_text(errors="ignore") for p in corpus_files]

    kept: dict[str, list[str]] = {}
    for candidate, aliases in candidates.items():
        hit_count = sum(
            1 for text in corpus_texts
            if _re.search(rf"\b{_re.escape(candidate)}\b", text, _re.IGNORECASE)
        )
        if hit_count / len(corpus_texts) < _BOILERPLATE_MATCH_THRESHOLD:
            kept[candidate] = aliases
    return kept


# Ticker symbols don't fuzzy-match company names well ("Nvidia" vs "NVDA" scores ~36),
# so resolution needs an explicit symbol-to-name reference, not bare string distance
# against the ticker alone. This is a small seed map for the demo universe; a real
# deployment would source it from a reference data feed (e.g. the SEC company
# tickers file) rather than hardcoding it.
KNOWN_COMPANY_NAMES: dict[str, str] = {
    "NVDA": "NVIDIA Corporation",
    "AMD": "Advanced Micro Devices",
    "INTC": "Intel Corporation",
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "AGG": "iShares Core U.S. Aggregate Bond ETF",
    "GLD": "SPDR Gold Shares",
    "BIL": "SPDR Bloomberg 1-3 Month T-Bill ETF",
}

# Narrow, curated executive-name -> ticker map for person-to-company resolution (e.g.
# a news article about "Jensen Huang" should recognize NVDA even if "NVIDIA"/"NVDA"
# never appears elsewhere in the text). Intentionally small and explicit -- same
# philosophy as every other alias list in this codebase -- not a general person/entity
# resolution system. Extend as needed for other held companies' named executives.
EXECUTIVE_NAME_TO_TICKER: dict[str, str] = {
    "jensen huang": "NVDA",
    "lisa su": "AMD",
    "brian chesky": "ABNB",
    "satya nadella": "MSFT",
    "tim cook": "AAPL",
    "andy jassy": "AMZN",
}

_DIRECT_MENTION_TITLE_CACHE: dict[str, str | None] = {}


def _company_title_word(symbol: str) -> str | None:
    """The first significant word of `symbol`'s real SEC-registered title (e.g.
    "AIRBNB" from "AIRBNB INC", "NVIDIA" from "NVIDIA CORP") -- the short form a real
    news headline actually uses, for any ticker, not just the 8 in the small
    hand-curated KNOWN_COMPANY_NAMES map. Cached in-process; a lookup failure (offline,
    unrecognized ticker) caches None so it isn't retried every call in the same run."""
    if symbol not in _DIRECT_MENTION_TITLE_CACHE:
        try:
            title = get_company_title_for_ticker(symbol)
        except Exception:
            title = None
        if title:
            first_word = title.split()[0]
            title = first_word if len(first_word) >= 3 else None
        _DIRECT_MENTION_TITLE_CACHE[symbol] = title
    return _DIRECT_MENTION_TITLE_CACHE[symbol]


def direct_mention_aliases(symbol: str) -> list[str]:
    """Every alias that counts as `symbol` itself naming its own company: the bare
    ticker, its known full legal name, its real SEC title's first word, and any
    executive name mapped to it. Shared by `load_company_graph` (decides whether to
    add the node) and `alerts.relevance.check_relevance` (re-confirms the match
    against the node) so they can never disagree about what counts as a direct
    mention -- confirmed live this split caused a real bug: a node got added for a
    direct mention, but relevance checking used a narrower alias set (just the bare
    ticker + KNOWN_COMPANY_NAMES) and silently failed to re-find the same text."""
    aliases = [symbol]
    if symbol in KNOWN_COMPANY_NAMES:
        aliases.append(KNOWN_COMPANY_NAMES[symbol])
    title_word = _company_title_word(symbol)
    if title_word:
        aliases.append(title_word)
    aliases.extend(name for name, ticker in EXECUTIVE_NAME_TO_TICKER.items() if ticker == symbol)
    return aliases


def _symbol_directly_mentioned(symbol: str, text: str) -> bool:
    """True if `text` literally names `symbol` itself -- the bare ticker, its known
    full name, its real SEC title's first word, or a named executive mapped to it.
    This is a SEPARATE, always-on check from supplier/material/competitor edge
    extraction (which `strict_materials_only` legitimately gates to avoid the
    AMD-10-K-mentions-NVIDIA-as-a-competitor false positive) -- recognizing that an
    article is directly ABOUT a held company is a different, simpler question than
    "does it reveal a supply-chain relationship," and must not be suppressed by the
    same flag that guards the latter. Confirmed live: without this, real articles
    headlined "Prominent NVIDIA investors call for board to contemplate Huang's
    return" produced zero candidates at all under strict_materials_only, because the
    only path capable of recognizing "NVIDIA" was the free-form company-name
    extraction that flag deliberately disables."""
    aliases = direct_mention_aliases(symbol)
    return any(re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE) for alias in aliases)


@tool
def resolve_company_identity(name_or_symbol: str, known_symbols: list[str]) -> dict:
    """Fuzzy-resolve a free-text company name or ticker to one of the known portfolio
    symbols, matching against both the raw symbol and its known company name."""
    best_symbol, best_score = None, 0.0
    for symbol in known_symbols:
        candidates = [symbol]
        if symbol in KNOWN_COMPANY_NAMES:
            candidates.append(KNOWN_COMPANY_NAMES[symbol])
        score = max(fuzz.WRatio(name_or_symbol, candidate, processor=default_process) for candidate in candidates)
        if score > best_score:
            best_symbol, best_score = symbol, score
    resolved = best_score >= 70
    return {"resolved": resolved, "symbol": best_symbol if resolved else None, "confidence_score": best_score}


@tool
def load_company_graph(
    portfolio_symbols: list[str],
    fixtures_dir: str | None = None,
    event_description: str | None = None,
    strict_materials_only: bool = False,
) -> dict:
    """Build the verified exposure graph for a set of portfolio holdings, grounded in
    each holding's REAL, current 10-K (live-fetched for any ticker, not just a fixed
    demo set) -- never assume a holding is exposed to an event just because it shares
    a sector label with one that is.

    Two sources of edges, both requiring a literal textual match with its exact
    evidence sentence (never inferred from industry similarity alone):
    1. `KNOWN_SUPPLIER_ALIASES` -- the small curated chip-supply-chain seed list, still
       useful when a holding genuinely is a semiconductor company.
    2. If `event_description` is given, candidate entities/materials/technologies are
       extracted from that text (the same heuristic as `propose_candidate_entities`)
       and checked against each holding's own filing the same way -- so a
       utility's real exposure to a grid-materials event, or a software company's
       real exposure to a GPU-supply event, can be found on its own terms instead of
       only ever rediscovering chip-supplier relationships regardless of what the
       event or the portfolio actually are.

    Also returns each holding's real SEC industry classification (`industries`,
    keyed by symbol, e.g. "Electric Services" vs. "Semiconductors & Related Devices")
    so a holding with no established link can be explained ("this is a utility, not
    plausibly connected to a chip export event") instead of silently omitted.

    `strict_materials_only=True` skips the capitalized-multi-word-phrase candidate
    path (see `extract_candidate_entities`'s docstring) -- use this for news-derived
    event descriptions, where an arbitrary company name mentioned in passing is far
    more likely to be an incidental competitor/market-commentary mention than a
    genuine material/technology/sanctions-relevant entity.
    """
    edges: list[ExposureEdge] = []
    industries: dict[str, str | None] = {}
    not_found: list[str] = []

    candidate_aliases: dict[str, list[str]] = {}
    if event_description:
        for candidate in extract_candidate_entities(
            event_description, max_candidates=15, include_phrases=not strict_materials_only
        ):
            candidate_aliases[candidate] = [candidate]
        candidate_aliases = _filter_boilerplate_candidates(candidate_aliases, fixtures_dir)

    for symbol in portfolio_symbols:
        filing = retrieve_company_filings(symbol, fixtures_dir=fixtures_dir)
        if not filing["found"]:
            not_found.append(symbol)
            industries[symbol] = None
            continue

        industries[symbol] = filing.get("sic_description") or (filing["metadata"] or {}).get("sic_description")
        accession = (filing["metadata"] or {}).get("source_url", symbol)

        edges.extend(
            extract_supplier_edges_from_filing_text(
                company_symbol=symbol,
                filing_text=filing["text"],
                evidence_label=f"{symbol} 10-K ({accession})",
                supplier_aliases=KNOWN_SUPPLIER_ALIASES,
            )
        )
        if candidate_aliases:
            candidate_edges = extract_supplier_edges_from_filing_text(
                company_symbol=symbol,
                filing_text=filing["text"],
                evidence_label=f"{symbol} 10-K ({accession})",
                supplier_aliases=candidate_aliases,
            )
            # A candidate derived SOLELY from a generic industry/geography/mechanism
            # category word (e.g. "semiconductor", "Taiwan") is kept for Stage-1
            # recall, but relabeled so downstream code (alerts.relevance,
            # alerts.verification) treats it as an unverified candidate requiring
            # Stage-2 evidence verification, not as alert-worthy supplier evidence
            # on its own -- see research_tools.is_generic_category_term.
            #
            # Also applies to multi-word GEOGRAPHY phrases (e.g. "United Arab
            # Emirates") for the same reason the single-word country list exists --
            # confirmed live, once the regulatory feed was broadened beyond a narrow
            # semiconductor/export topic set, a real oil-pipe antidumping case against
            # the UAE matched NVDA purely because "United Arab Emirates" is a bare
            # geography phrase, no real connection. An earlier, broader version of
            # this fix treated EVERY multi-word phrase this way, but that's wrong: a
            # genuinely specific multi-word term like "Entity List" (the Commerce
            # Department's real export-control mechanism, deliberately NOT denylisted
            # earlier today precisely because AMD/NVDA's own 10-Ks substantively
            # discuss it) was caught by that blanket rule too and incorrectly
            # downgraded -- confirmed as a real regression and reverted. Geography
            # phrases are a closed, enumerable category (unlike "any multi-word
            # phrase"), so a curated denylist is the right, narrow tool here, same
            # philosophy as the single-word list.
            for edge in candidate_edges:
                if is_generic_category_term(edge.target) or edge.target in _GENERIC_GEOGRAPHY_PHRASES:
                    edge = edge.model_copy(update={"relationship_type": "generic_candidate"})
                edges.append(edge)

    graph = build_graph(edges)

    # Always-on direct-mention check -- independent of strict_materials_only, which
    # gates ONLY the supplier/material/competitor edge extraction above, never this.
    # A held company's own name appearing in the event/article text makes it a node
    # (and therefore a "direct" match downstream in alerts.relevance.check_relevance)
    # regardless of whether any supplier edge was found for it.
    direct_mentions: list[str] = []
    if event_description:
        for symbol in portfolio_symbols:
            if _symbol_directly_mentioned(symbol, event_description):
                graph.add_node(symbol)
                direct_mentions.append(symbol)

    result = export_graph_json(graph)
    result["industries"] = industries
    if not_found:
        result["symbols_without_filing_evidence"] = not_found
    if direct_mentions:
        result["direct_mentions"] = direct_mentions
    return result


@tool
def find_direct_exposure_tool(graph_json: dict, event_entities: list[str]) -> dict:
    """Which of the named event entities are literally present as nodes in the
    exposure graph (direct exposure), vs. absent (no established direct link)."""
    nodes = {n["id"] for n in graph_json["nodes"]}
    direct = [e for e in event_entities if e in nodes]
    unknown = [e for e in event_entities if e not in nodes]
    return {"direct_exposure": direct, "no_established_link": unknown}


def _rebuild_graph(graph_json: dict):
    import networkx as nx

    g = nx.DiGraph()
    for edge in graph_json["edges"]:
        g.add_edge(edge["source"], edge["target"], **{k: v for k, v in edge.items() if k not in ("source", "target")})
    for node in graph_json["nodes"]:
        g.add_node(node["id"])
    return g


@tool
def traverse_relationships_tool(graph_json: dict, start_nodes: list[str], max_hops: int = 2) -> dict:
    """Walk the exposure graph outward from the given nodes to find indirect
    (multi-hop) exposure, returning each reached node's hop distance."""
    graph = _rebuild_graph(graph_json)
    distances = traverse_relationships(graph, start_nodes, max_hops=max_hops)
    return {"hop_distances": distances}


@tool
def calculate_exposure_weights(
    portfolio_weights: dict[str, float],
    direct_exposure_symbols: list[str],
    hop_distances: dict[str, int],
) -> dict:
    """Classify each portfolio holding's exposure to an event: 'direct' if the
    holding is itself named by the event (from find_direct_exposure_tool), 'indirect'
    if it is only reached via a supplier/customer relationship at some hop distance
    (from traverse_relationships_tool), or 'no_established_link' if neither applies --
    which must be reported as such, not silently treated as zero exposure.
    """
    direct_set = set(direct_exposure_symbols)
    exposure = {}
    for symbol, weight in portfolio_weights.items():
        if symbol in direct_set:
            exposure_type, hop = "direct", 0
        elif symbol in hop_distances:
            exposure_type, hop = "indirect", hop_distances[symbol]
        else:
            exposure_type, hop = "no_established_link", None
        exposure[symbol] = {
            "portfolio_weight": weight,
            "hop_distance_to_event": hop,
            "exposure_type": exposure_type,
        }
    return {"exposure": exposure}


@tool
def hybrid_search_evidence(query: str, filing_symbol: str, fixtures_dir: str | None = None) -> dict:
    """Search ONE company's real 10-K for evidence of a free-form query (any
    material, technology, event, or entity the agent itself is asking about --
    not limited to a hardcoded industry/country/material list), combining two
    independent evidence sources:

    1. `literal_matches` -- exact, word-boundary textual matches (via the same
       mechanism as the exposure graph's candidate-entity check). This is the
       STRONGER evidence: a literal match means the company's own filing names
       the exact term.
    2. `semantic_evidence` -- embedding-based retrieval (the real Bedrock
       Knowledge Base when configured/available, else the local TF-IDF
       fallback), for RECALL when the query is paraphrased or no literal term
       match exists (e.g. a filing discusses "burning coal to generate
       electricity" without using the query's exact wording).

    Always prefer `literal_matches` when both are present -- they are a
    stronger, more specific claim than a semantic passage, which may be merely
    topically related rather than a direct confirmation. Returns `found: False`
    only if NEITHER source turned up anything, which should be reported as a
    genuine absence of evidence, not treated as equivalent to a verified link.
    """
    graph_json = load_company_graph([filing_symbol], fixtures_dir=fixtures_dir, event_description=query)
    symbol_upper = filing_symbol.upper()
    literal_edges = [e for e in graph_json.get("edges", []) if e.get("source") == symbol_upper]
    literal_matches = [
        {
            "matched_entity": e.get("target"),
            "evidence_source": e.get("evidence_source"),
            "confidence": e.get("confidence"),
        }
        for e in literal_edges
    ]

    semantic = summarize_event_evidence(event_title=query, filing_symbol=filing_symbol, fixtures_dir=fixtures_dir)

    return {
        "found": bool(literal_matches) or semantic.get("found", False),
        "literal_matches": literal_matches,
        "semantic_evidence": semantic.get("evidence_context", ""),
        "semantic_retriever_used": semantic.get("retriever_used"),
        "industry": graph_json.get("industries", {}).get(symbol_upper),
        "no_filing_evidence": symbol_upper in (graph_json.get("symbols_without_filing_evidence") or []),
    }


ALL_EXPOSURE_TOOLS = [
    resolve_company_identity,
    load_company_graph,
    find_direct_exposure_tool,
    traverse_relationships_tool,
    calculate_exposure_weights,
    hybrid_search_evidence,
]
