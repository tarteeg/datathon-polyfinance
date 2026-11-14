from pydantic import BaseModel, Field

from app.integrations.stocksfeed.service import fetch_most_mentioned
from app.modules.chat.stock import StockQuery
from app.modules.stocks.schemas import Period


class StockComparison(BaseModel):
    tickers: list[str] = Field(min_length=2, description="Yahoo Finance symbols to compare.")
    period: Period = "1mo"
    show_chart: bool = False


class CompanyDiscovery(BaseModel):
    sector: str | None = Field(default=None, description="Company sector, e.g. Information Technology or Energy.")
    hours: int = Field(default=24, ge=1, le=168)
    limit: int = Field(default=5, ge=1, le=100)
    comparison_period: Period | None = Field(description="Required: null for coverage alone; mtd for which discovered company gained most this month, 1d for today.")


COMPARE_TOOL = {"toolSpec": {
    "name": "compare_stocks",
    "description": "Compare named stocks over one shared price-history period. Default to the trailing month for an unspecified performance period.",
    "inputSchema": {"json": StockComparison.model_json_schema()},
}}

DISCOVER_TOOL = {"toolSpec": {
    "name": "discover_companies",
    "description": "Discover S&P 500 companies receiving news coverage, optionally by sector. Ranked by distinct StocksFeed articles in the last 1–168 hours. Include comparison_period in the same call whenever the question mentions gains, movers, a winner or price performance of discovered companies.",
    "inputSchema": {"json": CompanyDiscovery.model_json_schema()},
}}


def discover(query: CompanyDiscovery):
    ranking = fetch_most_mentioned(query.sector, query.hours, query.limit)
    return {"sector": query.sector, "hours": ranking["hours"], "asOf": ranking["as_of"], "stocks": ranking["stocks"]}


def comparison_queries(tickers, period, show_chart=False):
    return [StockQuery(ticker=symbol, period=period, show_chart=show_chart)
            for symbol in dict.fromkeys(t.upper().strip() for t in tickers)]
