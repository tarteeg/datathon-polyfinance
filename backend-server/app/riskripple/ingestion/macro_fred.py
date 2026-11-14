"""FRED macroeconomic series ingestion via the public fredgraph.csv endpoint.

This endpoint requires no API key (unlike the FRED JSON API). It returns a two-column
CSV: observation_date, <series_id>. Good enough for treasury yields and similar daily
series used as risk-free-rate inputs and macro context.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import pandas as pd

from app.riskripple.schemas.provenance import SourceMetadata

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# A few series useful for risk-free-rate and macro-context inputs.
COMMON_SERIES = {
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "DGS3MO": "3-Month Treasury Constant Maturity Rate",
    "DFF": "Federal Funds Effective Rate",
    "CPIAUCSL": "CPI for All Urban Consumers",
}


@dataclass
class FredSeriesResult:
    series_id: str
    observations: pd.Series  # indexed by date, float value ("." entries dropped as missing)
    metadata: SourceMetadata


def fetch_series(series_id: str, *, client: httpx.Client | None = None) -> FredSeriesResult:
    own_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        resp = client.get(FRED_CSV_URL, params={"id": series_id})
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    df = pd.read_csv(io.StringIO(raw.decode("utf-8")))
    df.columns = ["observation_date", series_id]
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")  # FRED uses "." for missing
    series = df.set_index("observation_date")[series_id].dropna()

    metadata = SourceMetadata(
        source_name=f"FRED series {series_id} ({COMMON_SERIES.get(series_id, 'unlisted series')})",
        source_url=str(resp.url),
        retrieved_at=datetime.now(timezone.utc),
        observation_date=series.index.max().date() if len(series) else None,
        currency="USD",
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction=(
            "Federal Reserve Economic Data (FRED), public domain / free to use with "
            "attribution per FRED's terms of use."
        ),
    )
    return FredSeriesResult(series_id=series_id, observations=series, metadata=metadata)
