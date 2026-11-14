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
from app.riskripple.schemas.models import ExposureEdge
from app.riskripple.tools.regulatory_tools import retrieve_company_filings


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
def load_company_graph(portfolio_symbols: list[str], fixtures_dir: str | None = None) -> dict:
    """Build the verified supplier relationship graph for a set of portfolio holdings
    by scanning each company's 10-K text for literal mentions of known suppliers."""
    edges: list[ExposureEdge] = []
    for symbol in portfolio_symbols:
        filing = retrieve_company_filings(symbol, fixtures_dir=fixtures_dir)
        if not filing["found"]:
            continue
        accession = (filing["metadata"] or {}).get("source_url", symbol)
        edges.extend(
            extract_supplier_edges_from_filing_text(
                company_symbol=symbol,
                filing_text=filing["text"],
                evidence_label=f"{symbol} 10-K ({accession})",
                supplier_aliases=KNOWN_SUPPLIER_ALIASES,
            )
        )
    graph = build_graph(edges)
    return export_graph_json(graph)


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
