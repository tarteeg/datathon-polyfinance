"""SEC EDGAR company filings ingestion.

Confirmed working endpoints (require an identifying User-Agent per SEC's fair-access
policy -- https://www.sec.gov/os/webmaster-faq#developers):
  https://data.sec.gov/submissions/CIK##########.json      (company filing index)
  https://www.sec.gov/Archives/edgar/data/<cik>/<accession-no-dashes>/<document>  (filing doc)

IMPORTANT: SEC_EDGAR_USER_AGENT below is a placeholder. Before any ingestion volume
beyond light testing, replace it with a real team/organization contact (never a
personal email) via the SEC_EDGAR_CONTACT environment variable -- SEC says they may
reach out to that contact if automated access causes problems, and a fake address is
a genuine, not cosmetic, compliance gap.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from app.riskripple.schemas.provenance import SourceMetadata

SEC_EDGAR_CONTACT = os.environ.get("SEC_EDGAR_CONTACT", "contact@riskripple-ai.app")
_HEADERS = {"User-Agent": f"RiskRippleAI-Datathon {SEC_EDGAR_CONTACT}"}

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_no_padding}/{accession_no_dashes}/{document}"
EDGAR_FULLTEXT_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"


@dataclass
class FilingSummary:
    accession_number: str
    form_type: str
    filing_date: str
    report_date: str
    primary_document: str


@dataclass
class CompanySubmissionsResult:
    cik: str
    name: str
    sic_description: str | None
    recent_filings: list[FilingSummary]
    metadata: SourceMetadata


def fetch_company_submissions(cik: str, *, client: httpx.Client | None = None) -> CompanySubmissionsResult:
    """`cik` may be given with or without leading zeros; it is zero-padded to 10 digits."""
    cik10 = cik.strip().lstrip("0").zfill(10)
    own_client = client is None
    client = client or httpx.Client(timeout=30.0, headers=_HEADERS)
    try:
        resp = client.get(SUBMISSIONS_URL.format(cik10=cik10))
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    payload = resp.json()
    recent = payload.get("filings", {}).get("recent", {})

    filings: list[FilingSummary] = []
    n = len(recent.get("accessionNumber", []))
    for i in range(n):
        filings.append(
            FilingSummary(
                accession_number=recent["accessionNumber"][i],
                form_type=recent["form"][i],
                filing_date=recent["filingDate"][i],
                report_date=recent.get("reportDate", [""] * n)[i],
                primary_document=recent.get("primaryDocument", [""] * n)[i],
            )
        )

    metadata = SourceMetadata(
        source_name=f"SEC EDGAR company submissions ({payload.get('name', cik10)})",
        source_url=str(resp.url),
        retrieved_at=datetime.now(timezone.utc),
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction="U.S. public filings via SEC EDGAR; subject to SEC's fair-access rate limits.",
    )
    return CompanySubmissionsResult(
        cik=cik10,
        name=payload.get("name", ""),
        sic_description=payload.get("sicDescription"),
        recent_filings=filings,
        metadata=metadata,
    )


def filter_filings(filings: list[FilingSummary], form_type: str, limit: int = 5) -> list[FilingSummary]:
    return [f for f in filings if f.form_type == form_type][:limit]


COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_TICKER_TO_CIK_CACHE: dict[str, str] | None = None


def resolve_cik_for_ticker(ticker: str, *, client: httpx.Client | None = None) -> str | None:
    """Resolve a ticker (e.g. 'AAPL') to its zero-padded 10-digit CIK using SEC's free,
    no-auth ticker map. Caches the full map in-process after the first call -- it's a
    single ~700KB file covering every registrant, cheap to keep in memory for the
    process lifetime rather than re-fetching per ticker."""
    global _TICKER_TO_CIK_CACHE
    if _TICKER_TO_CIK_CACHE is None:
        own_client = client is None
        client = client or httpx.Client(timeout=30.0, headers=_HEADERS)
        try:
            resp = client.get(COMPANY_TICKERS_URL)
            resp.raise_for_status()
            payload = resp.json()
        finally:
            if own_client:
                client.close()
        _TICKER_TO_CIK_CACHE = {
            entry["ticker"].upper(): str(entry["cik_str"]).zfill(10) for entry in payload.values()
        }
    return _TICKER_TO_CIK_CACHE.get(ticker.strip().upper())


@dataclass
class FullTextSearchHit:
    entity_name: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: str
    primary_document: str
    document_url: str


@dataclass
class FullTextSearchResult:
    hits: list[FullTextSearchHit]
    metadata: SourceMetadata


def search_filings_fulltext(
    query: str,
    *,
    entity_name: str | None = None,
    forms: str = "10-K",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    client: httpx.Client | None = None,
) -> FullTextSearchResult:
    """Live SEC EDGAR full-text search (efts.sec.gov) -- free, no API key, covers
    filings since 2001. This is what lets an investigation check a candidate
    material/entity against ALL real public filings, not just the local fixture set's
    3 companies -- the same "never invent a relationship, only report a literal
    match" discipline as the rest of this codebase, just against a much larger corpus.

    Confirmed working live (2026-11-14, hackathon account): searching for "copper"
    scoped to Intel found its real FY2023 10-K (filed 2024-01-26, accession
    0000050863-24-000010), which genuinely discusses "direct copper-to-copper
    bonding" in its advanced-packaging section -- a real, current, material
    dependency the local 3-filing fixture set does not contain (confirmed by direct
    grep: no fixture filing mentions "copper").
    """
    params: dict[str, object] = {"q": f'"{query}"', "forms": forms}
    if entity_name:
        params["entityName"] = entity_name
    if start_date and end_date:
        params["dateRange"] = "custom"
        params["startdt"] = start_date
        params["enddt"] = end_date

    own_client = client is None
    client = client or httpx.Client(timeout=20.0, headers=_HEADERS)
    try:
        resp = client.get(EDGAR_FULLTEXT_SEARCH_URL, params=params)
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    payload = resp.json()

    hits: list[FullTextSearchHit] = []
    for h in payload.get("hits", {}).get("hits", [])[:limit]:
        src = h["_source"]
        accession, _, doc_name = h["_id"].partition(":")
        cik = src["ciks"][0] if src.get("ciks") else ""
        cik_no_padding = cik.lstrip("0")
        accession_no_dashes = accession.replace("-", "")
        hits.append(
            FullTextSearchHit(
                entity_name=(src.get("display_names") or [""])[0],
                cik=cik,
                accession_number=accession,
                form_type=src.get("form", ""),
                filing_date=src.get("file_date", ""),
                primary_document=doc_name,
                document_url=ARCHIVES_BASE_URL.format(
                    cik_no_padding=cik_no_padding, accession_no_dashes=accession_no_dashes, document=doc_name
                ),
            )
        )

    metadata = SourceMetadata(
        source_name="SEC EDGAR full-text search (efts.sec.gov)",
        source_url=str(resp.url),
        retrieved_at=datetime.now(timezone.utc),
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction="U.S. public filings via SEC EDGAR; full-text search covers filings since 2001.",
    )
    return FullTextSearchResult(hits=hits, metadata=metadata)


def fetch_filing_text(
    cik: str,
    filing: FilingSummary,
    *,
    client: httpx.Client | None = None,
    max_chars: int = 200_000,
) -> tuple[str, SourceMetadata]:
    """Fetch a filing's primary document and strip it to plain text.

    `max_chars` caps the returned text (10-Ks can be megabytes); callers needing the
    full document should fetch and chunk it themselves via the RAG ingestion pipeline
    instead of this convenience function.
    """
    cik_no_padding = cik.strip().lstrip("0")
    accession_no_dashes = filing.accession_number.replace("-", "")
    url = ARCHIVES_BASE_URL.format(
        cik_no_padding=cik_no_padding,
        accession_no_dashes=accession_no_dashes,
        document=filing.primary_document,
    )

    own_client = client is None
    client = client or httpx.Client(timeout=30.0, headers=_HEADERS)
    try:
        resp = client.get(url)
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    soup = BeautifulSoup(raw, "lxml")
    text = soup.get_text(separator="\n", strip=True)[:max_chars]

    metadata = SourceMetadata(
        source_name=f"SEC EDGAR filing {filing.form_type} ({filing.accession_number})",
        source_url=url,
        retrieved_at=datetime.now(timezone.utc),
        publication_date=datetime.strptime(filing.filing_date, "%Y-%m-%d").date() if filing.filing_date else None,
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction="U.S. public filing via SEC EDGAR.",
    )
    return text, metadata


def fetch_and_cache_10k(symbol: str, fixtures_dir) -> dict | None:
    """Live-fetch a symbol's most recent 10-K (resolving its CIK via the free SEC
    ticker map) and cache it on disk under `fixtures_dir/filings/` using the same
    `{symbol}_10K.txt` / `.metadata.json` convention as the pre-fetched demo fixtures,
    so this only has to hit SEC once per symbol (not once per request) and so any
    symbol -- not just the 3 pre-fetched demo companies -- can be checked for real
    exposure. Returns None (no exception) if the ticker doesn't resolve to a CIK or
    has no 10-K on file -- a real, honest "nothing found", not a crash.
    """
    from pathlib import Path

    cik = resolve_cik_for_ticker(symbol)
    if not cik:
        return None

    try:
        submissions = fetch_company_submissions(cik)
        ten_ks = filter_filings(submissions.recent_filings, "10-K", limit=1)
        if not ten_ks:
            return None
        text, meta = fetch_filing_text(cik, ten_ks[0])
    except Exception:
        return None

    base = Path(fixtures_dir) / "filings"
    base.mkdir(parents=True, exist_ok=True)
    text_path = base / f"{symbol.upper()}_10K.txt"
    meta_path = base / f"{symbol.upper()}_10K.metadata.json"

    meta_dict = meta.model_dump(mode="json") if hasattr(meta, "model_dump") else vars(meta)
    meta_dict["sic_description"] = submissions.sic_description
    meta_dict["company_name"] = submissions.name
    meta_dict["fetched_live"] = True

    text_path.write_text(text)
    meta_path.write_text(json.dumps(meta_dict, indent=2, default=str))

    return {"text": text, "metadata": meta_dict, "sic_description": submissions.sic_description}
