"""Shared provenance metadata. Every ingested dataset must carry one of these records
so that any figure shown in the UI can be traced back to a source, date, and currency
(see master spec section 7, "Required metadata")."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    source_name: str
    source_url: str
    retrieved_at: datetime
    observation_date: date | None = None
    publication_date: date | None = None
    currency: str | None = None
    data_version: str
    content_hash: str = Field(description="sha256 hex digest of the raw fetched payload")
    license_or_restriction: str = Field(
        description="Human-readable note on usage restrictions, e.g. rate limits or ToS caveats"
    )
