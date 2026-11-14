from fastapi import APIRouter, HTTPException

from app.integrations.yahoo import service as yahoo
from app.modules.stocks.schemas import Period, StockHistoryResponse

router = APIRouter(prefix="/stock", tags=["stocks"])


@router.get("/{ticker}/history", response_model=StockHistoryResponse)
def get_stock_history(ticker: str, period: Period = "1d"):
    """Return the latest regular-market quote and historical OHLCV candles."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise HTTPException(422, "Ticker is required")

    try:
        return {"history": yahoo.fetch_history(symbol, period)}
    except yahoo.YFTickerMissingError as exc:
        raise HTTPException(404, f"No market data for {symbol} in this period") from exc
    except yahoo.YFRateLimitError as exc:
        raise HTTPException(503, "Yahoo Finance rate limit reached") from exc
    except yahoo.MarketDataUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
