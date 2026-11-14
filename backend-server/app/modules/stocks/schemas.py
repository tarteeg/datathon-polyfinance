from typing import Literal

from pydantic import BaseModel


Period = Literal["1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "3y", "5y"]


class Quote(BaseModel):
    symbol: str
    name: str
    exchange: str | None = None
    currency: str | None
    previousClose: float | None = None
    regularMarketPrice: float
    regularMarketTime: int | None


class Candle(BaseModel):
    time: int
    Open: float
    High: float
    Low: float
    Close: float
    Volume: int | None


class StockHistory(BaseModel):
    ticker: Quote
    candles: list[Candle]


class StockHistoryResponse(BaseModel):
    history: StockHistory
