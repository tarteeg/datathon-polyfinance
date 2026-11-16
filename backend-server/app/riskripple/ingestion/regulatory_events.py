"""Regulatory/geopolitical event detection via the Federal Register API.

Source: https://www.federalregister.gov/developers/documentation/api/v1
Free, no API key, no observed rate limiting. This is the feed for Agent 1 (Regulatory
Watchdog): official U.S. government rule publications, filterable by agency, that
directly cover export-control and sanctions actions -- e.g. BIS "Additions and
Revisions to the Entity List" -- rather than generic news noise that would need much
more work to establish as a reliable, citable source.

GDELT (api.gdeltproject.org) was evaluated as a broader geopolitical-news supplement
but rate-limits aggressively (HTTP 429 under light testing) and was not wired in;
revisit if broader-than-U.S. event coverage becomes a priority.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.riskripple.schemas.provenance import SourceMetadata

FEDERAL_REGISTER_API_URL = "https://www.federalregister.gov/api/v1/documents.json"

# Agency slugs relevant to export-control / trade-restriction events (semiconductor
# scenario). See https://www.federalregister.gov/api/v1/agencies for the full list.
BIS_AGENCY_SLUG = "industry-and-security-bureau"
OFAC_AGENCY_SLUG = "foreign-assets-control-office"

# Broader default net for the live scheduled ingestion path (api/handlers/ingest.py).
# Deliberately not limited to "semiconductor export" -- that single hardcoded term was
# the reason a real event about an unrelated material/sector could never be detected
# at all, regardless of how good downstream relevance-matching is. This list is still
# a seed, not exhaustive; scripts/build_demo_snapshot.py intentionally keeps using the
# single original term so the frozen demo fixture (and the tests asserting exact alert
# counts against it) stays reproducible -- this broader list is only for the live path.
DEFAULT_REGULATORY_SEARCH_TERMS: list[str] = [
    "semiconductor export",
    "export administration regulations",
    "entity list addition",
    "critical minerals",
    "rare earth",
]


@dataclass
class RegulatoryDocument:
    document_number: str
    title: str
    publication_date: str
    agencies: list[str]
    document_url: str
    abstract: str | None


@dataclass
class RegulatoryDocumentsResult:
    documents: list[RegulatoryDocument]
    metadata: SourceMetadata


def search_documents(
    *,
    term: str = "",
    agency_slugs: list[str] | None = None,
    per_page: int = 20,
    client: httpx.Client | None = None,
) -> RegulatoryDocumentsResult:
    """Search Federal Register publications by keyword and (optionally) agency.

    Used to detect new/changed regulatory events relevant to a sector or jurisdiction,
    e.g. term="semiconductor export" + agency_slugs=[BIS_AGENCY_SLUG]. An empty/falsy
    `term` omits the keyword condition entirely rather than sending a literal empty
    string to the API -- confirmed live this still returns real, current documents
    (the newest ones across every agency), which is what `search_documents_broad`
    relies on for topic-agnostic coverage.
    """
    params: dict[str, object] = {
        "per_page": per_page,
        "order": "newest",
    }
    if term:
        params["conditions[term]"] = term
    if agency_slugs:
        params["conditions[agencies][]"] = agency_slugs

    own_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        resp = client.get(FEDERAL_REGISTER_API_URL, params=params)
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    payload = resp.json()

    documents = [
        RegulatoryDocument(
            document_number=r["document_number"],
            title=r["title"],
            publication_date=r["publication_date"],
            agencies=[a.get("name", "") for a in r.get("agencies", [])],
            document_url=r.get("html_url", ""),
            abstract=r.get("abstract"),
        )
        for r in payload.get("results", [])
    ]

    metadata = SourceMetadata(
        source_name="Federal Register API (federalregister.gov)",
        source_url=str(resp.url),
        retrieved_at=datetime.now(timezone.utc),
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction="U.S. government public domain publication; official and free, no API key required.",
    )
    return RegulatoryDocumentsResult(documents=documents, metadata=metadata)


def search_documents_broad(
    *,
    per_page: int = 40,
    client: httpx.Client | None = None,
) -> RegulatoryDocumentsResult:
    """Fetch the most recent Federal Register documents across EVERY agency/topic --
    no keyword term, no agency filter. `DEFAULT_REGULATORY_SEARCH_TERMS` (and
    `search_documents_multi`, which still exists unchanged for any caller that wants
    topic-scoped search) only ever look for semiconductor/export-control-flavored
    phrases, so a real regulatory action in an unrelated domain (an FDA recall rule,
    an FTC antitrust action, a DOL labor rule, an EPA rule unrelated to critical
    minerals) was never even fetched, regardless of how good downstream relevance-
    matching is. This is the fix: cast the widest real net the API allows (bounded by
    `per_page`, not a topic filter) and let the existing evidence-gated relevance
    check (`alerts.relevance.check_relevance`) and Stage-2 verification
    (`alerts.verification.classify_match`) -- both already proven to correctly reject
    irrelevant documents -- do the actual filtering, instead of pre-filtering by topic
    keyword before anything downstream ever sees it.
    """
    return search_documents(per_page=per_page, client=client)


def search_documents_multi(
    *,
    terms: list[str] | None = None,
    agency_slugs: list[str] | None = None,
    per_page: int = 20,
    client: httpx.Client | None = None,
) -> RegulatoryDocumentsResult:
    """Run `search_documents` once per term in `terms` (default:
    DEFAULT_REGULATORY_SEARCH_TERMS) and return the union, deduplicated by
    `document_number`. This is what turns "only ever looks for one fixed phrase" into
    "casts a wider net" without requiring any agent/LLM involvement -- a real, if
    still finite, improvement over a single hardcoded term.
    """
    terms = terms or DEFAULT_REGULATORY_SEARCH_TERMS
    own_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        seen: dict[str, RegulatoryDocument] = {}
        last_metadata: SourceMetadata | None = None
        for term in terms:
            result = search_documents(term=term, agency_slugs=agency_slugs, per_page=per_page, client=client)
            last_metadata = result.metadata
            for doc in result.documents:
                seen.setdefault(doc.document_number, doc)
    finally:
        if own_client:
            client.close()

    assert last_metadata is not None  # terms is never empty
    return RegulatoryDocumentsResult(documents=list(seen.values()), metadata=last_metadata)
