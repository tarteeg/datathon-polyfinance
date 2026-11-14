"""Deterministic relevance check: does a regulatory/sanctions document connect to a
specific real portfolio, directly (names a held company) or indirectly (names an
entity/material already present in that portfolio's real, event-aware exposure graph
from `exposure_tools.load_company_graph`)?

Adapted from riskripple-ai's `alerts/relevance.py`. That version used a hardcoded
`PORTFOLIO_COMPANY_ALIASES` dict covering exactly 3 demo tickers (NVDA/AMD/INTC) --
the same portfolio-adaptiveness bug fixed in `exposure_tools.load_company_graph`. This
version drops the hardcoded alias dict entirely: a portfolio symbol's only alias is
the ticker itself (checked case-insensitively, word-boundary), and every other graph
node is already a literal string found in a real filing (either a known supplier name
or an event-derived candidate), so it's already its own alias. No portfolio- or
industry-specific seed list required -- this generalizes to any real holding.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.riskripple.tools.exposure_tools import KNOWN_COMPANY_NAMES

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class RelevanceMatch:
    symbol: str  # the portfolio holding this match is relevant to
    relationship: str  # "direct" | "supply_chain"
    node_id: str  # the canonical exposure-graph node that matched (== symbol for "direct")
    matched_entity: str  # the literal alias text actually found in the document
    evidence_snippet: str
    # True when this match's ONLY basis is a generic industry/geography/mechanism
    # category word (edge relationship_type == "generic_candidate" from
    # exposure_tools.load_company_graph) -- a Stage-1 candidate that still needs
    # Stage-2 evidence verification (alerts.verification.classify_match) before it
    # may become a recorded alert. False for direct matches and for matches on a
    # specific material/known-supplier/company name, which are already real evidence.
    needs_verification: bool = False


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


def check_relevance(document_text: str, graph_json: dict, portfolio_symbols: list[str]) -> list[RelevanceMatch]:
    """`graph_json` is the output of `exposure_tools.load_company_graph` for this
    portfolio, built with `event_description` set to this same document's
    title+abstract -- so its edges already reflect this specific document's
    candidate entities, not just the fixed chip-supplier seed list.
    """
    portfolio_set = set(portfolio_symbols)
    matches: list[RelevanceMatch] = []
    seen: set[tuple[str, str]] = set()

    for node in graph_json.get("nodes", []):
        node_id = node["id"]
        # A ticker symbol rarely appears literally in news/regulatory prose ("NVDA"
        # vs. "NVIDIA") -- try the known full company name too when this node is a
        # portfolio symbol we have a name for. This is a best-effort lookup against
        # the existing small reference table (exposure_tools.KNOWN_COMPANY_NAMES),
        # not a new hardcoded alias list; a ticker with no entry there just falls
        # back to matching on the bare symbol, same as any other graph node.
        aliases = [node_id]
        if node_id in portfolio_set and node_id in KNOWN_COMPANY_NAMES:
            aliases.append(KNOWN_COMPANY_NAMES[node_id])

        hit, matched_alias = None, None
        for alias in aliases:
            hit = _word_match(alias, document_text)
            if hit:
                matched_alias = alias
                break
        if not hit:
            continue

        if node_id in portfolio_set:
            key = (node_id, "direct")
            if key not in seen:
                seen.add(key)
                matches.append(
                    RelevanceMatch(
                        symbol=node_id,
                        relationship="direct",
                        node_id=node_id,
                        matched_entity=matched_alias,
                        evidence_snippet=_sentence_containing(document_text, hit),
                    )
                )
        else:
            # Not a portfolio symbol itself -- a supplier/material/candidate node.
            # Find which held companies have a real, extracted edge pointing to it.
            for edge in graph_json.get("edges", []):
                if edge["target"] == node_id and edge["source"] in portfolio_set:
                    key = (edge["source"], "supply_chain")
                    if key in seen:
                        continue
                    seen.add(key)
                    matches.append(
                        RelevanceMatch(
                            symbol=edge["source"],
                            relationship="supply_chain",
                            node_id=node_id,
                            matched_entity=matched_alias,
                            evidence_snippet=_sentence_containing(document_text, hit),
                            needs_verification=(edge.get("relationship_type") == "generic_candidate"),
                        )
                    )
    return matches
