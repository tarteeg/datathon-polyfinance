"""Agent 3 (Exposure and Contagion Mapper) tool surface."""
from __future__ import annotations

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
from app.riskripple.schemas.models import ExposureEdge
from app.riskripple.tools.regulatory_tools import retrieve_company_filings
from app.riskripple.tools.research_tools import extract_candidate_entities

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
            edges.extend(
                extract_supplier_edges_from_filing_text(
                    company_symbol=symbol,
                    filing_text=filing["text"],
                    evidence_label=f"{symbol} 10-K ({accession})",
                    supplier_aliases=candidate_aliases,
                )
            )

    graph = build_graph(edges)
    result = export_graph_json(graph)
    result["industries"] = industries
    if not_found:
        result["symbols_without_filing_evidence"] = not_found
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


ALL_EXPOSURE_TOOLS = [
    resolve_company_identity,
    load_company_graph,
    find_direct_exposure_tool,
    traverse_relationships_tool,
    calculate_exposure_weights,
]
