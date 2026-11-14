"""Company relationship graph (Agent 3: Exposure and Contagion Mapper).

Relationships are only created when supported by literal evidence (a sentence from a
real filing, or a static ETF-holdings fact); nothing here is inferred from
same-industry membership alone. Per the master spec: "Do not invent company
relationships. When relationship evidence is unavailable, return an unknown result."
"""
from __future__ import annotations

import re

import networkx as nx

from app.riskripple.schemas.models import ExposureEdge

# Known supplier/partner names to look for in filing text, with simple alias patterns.
# This is a small, explicit seed list -- not a general NER model -- so every edge it
# produces is traceable to a literal keyword match in the source sentence.
KNOWN_SUPPLIER_ALIASES: dict[str, list[str]] = {
    "TSMC": ["Taiwan Semiconductor Manufacturing", "TSMC"],
    "Samsung": ["Samsung Electronics", "Samsung"],
    "SK Hynix": ["SK Hynix"],
    "Micron": ["Micron Technology", "Micron"],
    "Hon Hai (Foxconn)": ["Hon Hai Precision"],
    "Wistron": ["Wistron Corporation"],
    "Fabrinet": ["Fabrinet"],
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def extract_supplier_edges_from_filing_text(
    *,
    company_symbol: str,
    filing_text: str,
    evidence_label: str,
    supplier_aliases: dict[str, list[str]] | None = None,
) -> list[ExposureEdge]:
    """Scan filing text for sentences naming a known supplier and create one edge per
    (company, supplier) pair found, with the matching sentence as evidence.

    Deliberately conservative: only produces an edge when a literal alias string is
    present in the text, and records the exact matching sentence, so every edge can be
    checked against its source rather than trusted blindly.
    """
    supplier_aliases = supplier_aliases or KNOWN_SUPPLIER_ALIASES
    sentences = _SENTENCE_SPLIT_RE.split(filing_text)

    edges: list[ExposureEdge] = []
    seen_suppliers: set[str] = set()
    for sentence in sentences:
        for supplier, aliases in supplier_aliases.items():
            if supplier in seen_suppliers:
                continue
            if any(alias.lower() in sentence.lower() for alias in aliases):
                snippet = sentence.strip()
                if len(snippet) > 300:
                    snippet = snippet[:300] + "..."
                edges.append(
                    ExposureEdge(
                        source=company_symbol,
                        target=supplier,
                        relationship_type="supplier",
                        evidence_source=f'{evidence_label}: "{snippet}"',
                        confidence="verified",
                    )
                )
                seen_suppliers.add(supplier)
    return edges


def build_graph(edges: list[ExposureEdge]) -> nx.DiGraph:
    g = nx.DiGraph()
    for edge in edges:
        g.add_edge(
            edge.source,
            edge.target,
            relationship_type=edge.relationship_type,
            evidence_source=edge.evidence_source,
            confidence=edge.confidence,
            observation_date=edge.observation_date,
        )
    return g


def find_direct_exposure(graph: nx.DiGraph, event_entities: list[str]) -> list[str]:
    """Nodes in the graph that are literally named by the event (not traversal)."""
    node_set = set(graph.nodes)
    return [e for e in event_entities if e in node_set]


def traverse_relationships(graph: nx.DiGraph, start_nodes: list[str], max_hops: int = 2) -> dict[str, int]:
    """BFS outward from the given nodes up to `max_hops`, returning each reached node's
    hop distance (1 = direct relationship, 2 = indirect, etc.). Nodes unreachable within
    max_hops are omitted -- callers should treat absence as "unknown exposure", not zero
    exposure.
    """
    distances: dict[str, int] = {}
    frontier = set(start_nodes) & set(graph.nodes)
    visited = set(frontier)
    hop = 0
    while frontier and hop < max_hops:
        hop += 1
        next_frontier = set()
        for node in frontier:
            for neighbor in list(graph.successors(node)) + list(graph.predecessors(node)):
                if neighbor not in visited:
                    distances[neighbor] = hop
                    next_frontier.add(neighbor)
        visited |= next_frontier
        frontier = next_frontier
    return distances


def export_graph_json(graph: nx.DiGraph, highlight_nodes: list[str] | None = None) -> dict:
    """Serialize to a React Flow / Cytoscape-friendly node/edge structure."""
    highlight = set(highlight_nodes or [])
    nodes = [{"id": n, "highlighted": n in highlight} for n in graph.nodes]
    edges = [
        {
            "source": u,
            "target": v,
            "relationship_type": data.get("relationship_type"),
            "confidence": data.get("confidence"),
            "evidence_source": data.get("evidence_source"),
        }
        for u, v, data in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}
