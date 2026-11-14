"""OFAC Specially Designated Nationals (SDN) list ingestion.

Source: https://ofac.treasury.gov/sanctions-list-service (Sanctions List Service API).
Confirmed working endpoint (redirects to the actual CSV export):
https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV

This is a structured, official source. Per the master spec, it is used only for
structured screening records (name/program/country), never as a vector-similarity
match for "is this entity sanctioned" -- that determination always requires an exact
or alias-resolved match against this structured list.
"""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.riskripple.schemas.provenance import SourceMetadata

SDN_CSV_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"

# Classic 12-column SDN.CSV schema, stable across OFAC's publication formats for years.
SDN_COLUMNS = [
    "ent_num",
    "sdn_name",
    "sdn_type",
    "program",
    "title",
    "call_sign",
    "vess_type",
    "tonnage",
    "grt",
    "vess_flag",
    "vess_owner",
    "remarks",
]


@dataclass
class SdnRecord:
    ent_num: str
    sdn_name: str
    sdn_type: str | None
    program: str | None
    remarks: str | None


@dataclass
class SdnListResult:
    records: list[SdnRecord]
    metadata: SourceMetadata


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return None if value in ("", "-0-") else value


def fetch_sdn_list(*, client: httpx.Client | None = None) -> SdnListResult:
    own_client = client is None
    client = client or httpx.Client(timeout=30.0, follow_redirects=True)
    try:
        resp = client.get(SDN_CSV_URL)
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    text = raw.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))

    records: list[SdnRecord] = []
    for row in reader:
        if len(row) < 4:
            continue
        padded = row + [""] * (len(SDN_COLUMNS) - len(row))
        fields = dict(zip(SDN_COLUMNS, padded))
        records.append(
            SdnRecord(
                ent_num=fields["ent_num"].strip(),
                sdn_name=_clean(fields["sdn_name"]) or "",
                sdn_type=_clean(fields["sdn_type"]),
                program=_clean(fields["program"]),
                remarks=_clean(fields["remarks"]),
            )
        )

    metadata = SourceMetadata(
        source_name="OFAC Specially Designated Nationals (SDN) List",
        source_url=str(resp.url),
        retrieved_at=datetime.now(timezone.utc),
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction=(
            "U.S. Treasury OFAC public sanctions data. Official source for U.S. "
            "sanctions screening; not a substitute for full legal compliance review."
        ),
    )
    return SdnListResult(records=records, metadata=metadata)
