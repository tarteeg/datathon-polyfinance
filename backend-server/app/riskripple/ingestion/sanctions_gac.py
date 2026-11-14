"""Global Affairs Canada consolidated autonomous sanctions list ingestion.

Source page: https://www.international.gc.ca/world-monde/international_relations-relations_internationales/sanctions/consolidated-consolide.aspx?lang=eng
Confirmed structured data file linked from that page:
https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml

Treated as an informational screening source per the master spec -- not a complete
substitute for the applicable Canadian sanctions regulations.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from xml.etree import ElementTree

import httpx

from app.riskripple.schemas.provenance import SourceMetadata

GAC_CONSOLIDATED_XML_URL = (
    "https://www.international.gc.ca/world-monde/assets/office_docs/"
    "international_relations-relations_internationales/sanctions/sema-lmes.xml"
)
GAC_SOURCE_PAGE_URL = (
    "https://www.international.gc.ca/world-monde/international_relations-relations_internationales/"
    "sanctions/consolidated-consolide.aspx?lang=eng"
)


@dataclass
class GacRecord:
    country: str | None
    last_name: str | None
    given_name: str | None
    entity_name: str | None
    schedule: str | None
    item_number: str | None
    date_of_listing: str | None


@dataclass
class GacListResult:
    records: list[GacRecord]
    metadata: SourceMetadata


def _text(record: ElementTree.Element, *tag_candidates: str) -> str | None:
    for tag in tag_candidates:
        el = record.find(tag)
        if el is not None and el.text:
            return el.text.strip()
    return None


def fetch_consolidated_list(*, client: httpx.Client | None = None) -> GacListResult:
    own_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        resp = client.get(GAC_CONSOLIDATED_XML_URL)
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    root = ElementTree.fromstring(raw)

    records: list[GacRecord] = []
    for record in root.findall("record"):
        records.append(
            GacRecord(
                country=_text(record, "Country-Pays"),
                last_name=_text(record, "LastName-NomDeFamille"),
                given_name=_text(record, "GivenName-Prenom"),
                entity_name=_text(record, "Entity-Entite"),
                schedule=_text(record, "Schedule-Annexe"),
                item_number=_text(record, "Item-NumeroDarticle"),
                date_of_listing=_text(record, "DateOfListing-DateDinscription"),
            )
        )

    metadata = SourceMetadata(
        source_name="Global Affairs Canada Consolidated Autonomous Sanctions List",
        source_url=GAC_CONSOLIDATED_XML_URL,
        retrieved_at=datetime.now(timezone.utc),
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction=(
            "Government of Canada open data. Informational screening source; not a "
            "complete substitute for the applicable sanctions regulations."
        ),
    )
    return GacListResult(records=records, metadata=metadata)
