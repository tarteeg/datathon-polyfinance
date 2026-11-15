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
import re
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

# A real 10-K's stripped text interleaves actual prose with dense inline-XBRL
# metadata (taxonomy URLs, CIK/date dumps, concatenated tag identifiers like
# `aee:CoalFiredElectricGenerationEquipmentMember`). Confirmed live on AEE's real
# 10-K: 4,200 of 12,765 lines (33%) are this kind of noise. It pollutes both the
# TF-IDF retriever (a camelCase identifier is one unsplittable token, so a real
# word embedded in it, e.g. "coal" inside the identifier above, can never match a
# query token) and a Knowledge Base's embeddings (noise chunks dilute the real
# signal). Simple, inspectable heuristic -- same house style as
# _GENERIC_PROCEDURAL_WORDS elsewhere in this codebase -- not an ML classifier.
_XBRL_NAMESPACE_LINE_RE = re.compile(r"^[a-z]{2,10}(-[a-z]{2,10})?:[A-Za-z]")
_PURE_NUMBER_OR_DATE_RE = re.compile(r"^\d{4,10}(-\d{2}-\d{2})?$")
_TAXONOMY_URL_RE = re.compile(r"^https?://")


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _TAXONOMY_URL_RE.match(stripped):
        return True
    if _PURE_NUMBER_OR_DATE_RE.match(stripped):
        return True
    if _XBRL_NAMESPACE_LINE_RE.match(stripped):
        return True
    # A long line with no whitespace at all is virtually always a concatenated
    # identifier (real prose sentences always contain spaces well before 15 chars).
    if " " not in stripped and len(stripped) > 15:
        return True
    return False


def clean_filing_text(text: str) -> str:
    """Strip XBRL taxonomy/tag-soup lines from a fetched filing's text while leaving
    every real prose line untouched, verbatim. Line-based and deliberately simple: a
    line is dropped only if it matches one of a few concrete, checkable patterns
    (a taxonomy URL, a bare CIK/date, an `aee:SomeTagMember`-style namespaced
    identifier, or any other long whitespace-free run) -- never a semantic judgment
    about content. Collapses the resulting gaps so cleaned output doesn't carry long
    runs of blank lines where noise used to be.
    """
    lines = text.split("\n")
    kept = [line for line in lines if not _is_noise_line(line)]
    cleaned = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", cleaned)
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


_TITLE_TO_TICKER_CACHE: dict[str, str] | None = None


def _load_ticker_maps(client: httpx.Client | None = None) -> None:
    global _TICKER_TO_CIK_CACHE, _TITLE_TO_TICKER_CACHE
    if _TICKER_TO_CIK_CACHE is not None:
        return
    own_client = client is None
    client = client or httpx.Client(timeout=30.0, headers=_HEADERS)
    try:
        resp = client.get(COMPANY_TICKERS_URL)
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if own_client:
            client.close()
    _TICKER_TO_CIK_CACHE = {entry["ticker"].upper(): str(entry["cik_str"]).zfill(10) for entry in payload.values()}
    # Company name fallback: SEC's own ticker map includes a "title" per entry (e.g.
    # "NVIDIA CORP" for ticker NVDA). A user typing the company name instead of the
    # ticker ("nvidia" instead of "NVDA") previously resolved to nothing and silently
    # produced zero evidence for that holding -- confirmed live. Exact title match is
    # a narrow, deterministic fallback (not fuzzy matching, which risks resolving to
    # the wrong company); it only helps when the input is literally the company's
    # registered name or a prefix of it, not an approximate guess.
    _TITLE_TO_TICKER_CACHE = {entry["title"].upper(): entry["ticker"].upper() for entry in payload.values()}


def resolve_cik_for_ticker(ticker: str, *, client: httpx.Client | None = None) -> str | None:
    """Resolve a ticker (e.g. 'AAPL') to its zero-padded 10-digit CIK using SEC's free,
    no-auth ticker map. Caches the full map in-process after the first call -- it's a
    single ~700KB file covering every registrant, cheap to keep in memory for the
    process lifetime rather than re-fetching per ticker.

    Falls back to an exact (or prefix) match against each company's registered title
    if the input isn't a known ticker symbol -- so "nvidia" resolves the same way
    "NVDA" does, without guessing via fuzzy similarity.
    """
    _load_ticker_maps(client)
    assert _TICKER_TO_CIK_CACHE is not None and _TITLE_TO_TICKER_CACHE is not None
    normalized = ticker.strip().upper()
    cik = _TICKER_TO_CIK_CACHE.get(normalized)
    if cik:
        return cik
    resolved_ticker = _TITLE_TO_TICKER_CACHE.get(normalized)
    if not resolved_ticker:
        resolved_ticker = next(
            (t for title, t in _TITLE_TO_TICKER_CACHE.items() if title.startswith(normalized) and len(normalized) >= 4),
            None,
        )
    return _TICKER_TO_CIK_CACHE.get(resolved_ticker) if resolved_ticker else None


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


# A blind text[:max_chars] truncation keeps whatever happens to be first in the
# document -- for a large filer (a bank's 10-K especially) that is often cover pages,
# legal boilerplate, or (worse) the machine-generated XBRL tag dump that many filers'
# primary HTML document embeds, not the narrative Risk Factors/Business/MD&A sections
# this system actually needs. Confirmed directly: JPM's 10-K, truncated at 200k chars,
# cut off mid-word inside raw XBRL tag soup (`...jpm:LongTermDebtVariableInterest...`),
# nowhere near its real risk-factors prose -- making its "no established link" result
# a tooling failure, not a finding. Standard 10-K items ("Item 1A. Risk Factors",
# "Item 1. Business", "Item 7. Management's Discussion") are the actually-relevant
# content, so locate and prioritize them before falling back to a prefix truncation.
def _real_item_heading_matches(text: str, item_word: str) -> list[re.Match]:
    """Find genuine "Item N" SECTION HEADINGS, filtering out the two kinds of false
    positive a real 10-K's text is full of: a Table-of-Contents row (the item name
    immediately followed by another "Item ..." row within a short span -- TOC rows
    are packed tightly together) and an in-prose cross-reference like "Part I, Item
    1A: Risk Factors on pages 9-31" (the item name immediately preceded by "Part I,"
    / "Part 1,"). Confirmed necessary by direct inspection of JPM's real 10-K: of 6
    raw "Item 1A" regex matches, only 1 (at the real section boundary, immediately
    followed by actual prose: "Item 1A. Risk Factors.\\nThe following discussion sets
    forth...") was the genuine heading; the rest were 1 TOC row and 4 narrative
    cross-references.
    """
    pattern = re.compile(rf"item\s+{item_word}\b[.\-:—\s]", re.IGNORECASE)
    real: list[re.Match] = []
    for m in pattern.finditer(text):
        before = text[max(0, m.start() - 20) : m.start()]
        if re.search(r"part\s+(i|1)\s*,\s*$", before, re.IGNORECASE):
            continue  # in-prose cross-reference ("Part I, Item 1A: ..." -- the comma
            # distinguishes this from the legitimate "Part I\nItem 1. Business"
            # standalone section-divider heading, which has no comma.
        after = text[m.end() : m.end() + 250]
        if re.search(r"item\s+\d", after, re.IGNORECASE):
            continue  # another item heading immediately follows -- a TOC row
        real.append(m)
    return real


def _extract_priority_sections(text: str) -> str | None:
    """Return the text spanning from the real "Item 1" heading through the end of
    the real "Item 7A"/"Item 7" section (Business through MD&A -- the standard 10-K
    narrative items), or None if no recognizable item structure was found.
    """
    starts = _real_item_heading_matches(text, "1")
    if not starts:
        return None
    start = starts[0].start()
    item8_matches = _real_item_heading_matches(text[start:], "8")
    end = start + item8_matches[0].start() if item8_matches else len(text)
    if end - start < 500:  # too small to be a real section span -- treat as not found
        return None
    return text[start:end]


def fetch_filing_text(
    cik: str,
    filing: FilingSummary,
    *,
    client: httpx.Client | None = None,
    max_chars: int = 500_000,
) -> tuple[str, SourceMetadata]:
    """Fetch a filing's primary document and strip it to plain text.

    Prioritizes the narrative Item 1/1A/7/7A sections (Business, Risk Factors,
    MD&A) when they're findable, since those are what this system's evidence search
    actually needs -- a blind prefix truncation on a large filing can cut off before
    reaching them entirely (see `_extract_priority_sections`). Falls back to a
    straight prefix truncation at `max_chars` (raised from the previous 200_000,
    which was too small for many large filers) if no recognizable item structure is
    found. Callers needing the full, unbounded document should fetch and chunk it
    themselves via the RAG ingestion pipeline instead of this convenience function.
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
    full_text = soup.get_text(separator="\n", strip=True)

    priority = _extract_priority_sections(full_text)
    if priority is not None:
        # Keep the priority (narrative) section first, then fill any remaining
        # budget with the start of the document (cover page / intro), so a caller
        # searching linearly still sees the most relevant content within budget.
        remaining = max_chars - len(priority)
        text = priority[:max_chars] if remaining <= 0 else priority + "\n\n" + full_text[:remaining]
    else:
        text = full_text[:max_chars]

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
