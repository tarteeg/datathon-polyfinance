"""Agent 1 (Regulatory Watchdog) and Agent 2 (Regulatory Intelligence Investigator)
tool surface. Reads from the frozen fixture snapshot by default; swap `fixtures_dir`
for the live S3 processed/ prefix in a deployed environment.
"""
from __future__ import annotations

import json
from pathlib import Path

from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process
from strands import tool

from app.riskripple.config import FIXTURES_DIR
from app.riskripple.ingestion import filings_sec
from app.riskripple.rag.chunking import chunk_document
from app.riskripple.rag.retrieval import LocalLexicalRetriever, build_evidence_context


@tool
def list_new_documents(fixtures_dir: str | None = None) -> dict:
    """List regulatory documents available for investigation (Federal Register BIS
    export-control publications in the demo fixture set)."""
    base = Path(fixtures_dir or FIXTURES_DIR) / "regulatory"
    path = base / "federal_register_bis_semiconductor.json"
    if not path.exists():
        return {"documents": [], "note": "no fixture found; run scripts/build_demo_snapshot.py"}
    documents = json.loads(path.read_text())
    return {"documents": documents, "count": len(documents)}


@tool
def search_sanctions_records(entity_name: str, fixtures_dir: str | None = None, score_cutoff: float = 80.0) -> dict:
    """Fuzzy-match a company/individual name against the frozen OFAC SDN and Global
    Affairs Canada consolidated sanctions lists. This is name-matching for screening
    triage only -- it is NOT a legal determination of sanctioned status, which
    requires exact identifier matching and compliance review."""
    base = Path(fixtures_dir or FIXTURES_DIR) / "regulatory"
    matches = []

    ofac_path = base / "ofac_sdn.json"
    if ofac_path.exists():
        records = json.loads(ofac_path.read_text())
        names = [r["sdn_name"] for r in records]
        for name, score, idx in process.extract(entity_name, names, scorer=fuzz.WRatio, processor=default_process, limit=5):
            if score >= score_cutoff:
                matches.append({"list": "OFAC SDN", "matched_name": name, "score": score, "program": records[idx].get("program")})

    gac_path = base / "gac_consolidated.json"
    if gac_path.exists():
        records = json.loads(gac_path.read_text())
        names = [
            (r.get("entity_name") or f"{r.get('given_name', '')} {r.get('last_name', '')}").strip()
            for r in records
        ]
        for name, score, idx in process.extract(entity_name, names, scorer=fuzz.WRatio, processor=default_process, limit=5):
            if score >= score_cutoff and name:
                matches.append({"list": "Global Affairs Canada Consolidated List", "matched_name": name, "score": score, "schedule": records[idx].get("schedule")})

    return {
        "query": entity_name,
        "matches": matches,
        "is_legal_sanctions_determination": False,
        "note": "Fuzzy name match for screening triage only; confirm with exact identifiers before any compliance conclusion.",
    }


@tool
def retrieve_company_filings(symbol: str, fixtures_dir: str | None = None) -> dict:
    """Load a company's 10-K text and source metadata (including its real SEC industry
    classification, `sic_description`). Checks the local cache first (the 3 pre-fetched
    demo fixtures, or any symbol fetched by a prior call); if a symbol isn't cached,
    live-fetches its real, current 10-K from SEC EDGAR (resolving its CIK from SEC's
    free ticker map) and caches it for next time. This means ANY real ticker can be
    checked for exposure, not just the 3 companies in the original demo fixture set --
    returns `found: False` only if the ticker genuinely has no resolvable CIK or no
    10-K on file, never because it merely wasn't pre-fetched."""
    resolved_dir = fixtures_dir or FIXTURES_DIR
    base = Path(resolved_dir) / "filings"
    text_path = base / f"{symbol.upper()}_10K.txt"
    meta_path = base / f"{symbol.upper()}_10K.metadata.json"

    if not text_path.exists():
        fetched = filings_sec.fetch_and_cache_10k(symbol, resolved_dir)
        if fetched is None:
            return {"found": False, "symbol": symbol}
        return {
            "found": True,
            "symbol": symbol,
            "text": fetched["text"],
            "metadata": fetched["metadata"],
            "sic_description": fetched["sic_description"],
        }

    metadata = json.loads(meta_path.read_text()) if meta_path.exists() else None
    return {
        "found": True,
        "symbol": symbol,
        "text": text_path.read_text(),
        "metadata": metadata,
        "sic_description": (metadata or {}).get("sic_description"),
    }


@tool
def resolve_entity_aliases(entity_name: str, known_aliases: dict[str, list[str]]) -> dict:
    """Resolve an entity name to a canonical id using a known alias map, via fuzzy
    matching. Returns None if no alias crosses the confidence threshold, rather than
    guessing."""
    best_canonical, best_score = None, 0.0
    for canonical, aliases in known_aliases.items():
        for alias in [canonical] + aliases:
            score = fuzz.WRatio(entity_name, alias, processor=default_process)
            if score > best_score:
                best_canonical, best_score = canonical, score
    if best_score < 85:
        return {"resolved": False, "query": entity_name}
    return {"resolved": True, "query": entity_name, "canonical_entity": best_canonical, "confidence_score": best_score}


@tool
def summarize_event_evidence(event_title: str, filing_symbol: str, fixtures_dir: str | None = None) -> dict:
    """Retrieve the most relevant passages from a company's 10-K for a given
    regulatory event title, using the local lexical retriever, and return a bounded,
    citation-bearing evidence context."""
    filing = retrieve_company_filings(filing_symbol, fixtures_dir=fixtures_dir)
    if not filing["found"]:
        return {"evidence_context": "", "found": False}

    chunks = chunk_document(
        document_id=f"{filing_symbol}_10K",
        text=filing["text"],
        title=f"{filing_symbol} 10-K",
        source_url=filing["metadata"]["source_url"] if filing["metadata"] else None,
    )
    retriever = LocalLexicalRetriever(chunks)
    results = retriever.retrieve(event_title, top_k=5)
    return {
        "found": len(results) > 0,
        "evidence_context": build_evidence_context(results),
        "n_chunks_retrieved": len(results),
    }


ALL_REGULATORY_TOOLS = [
    list_new_documents,
    search_sanctions_records,
    retrieve_company_filings,
    resolve_entity_aliases,
    summarize_event_evidence,
]
