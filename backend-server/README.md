# Stock market API

I built this FastAPI server to supply the dashboard with stock prices and news.

- `GET /stock/{ticker}/history` returns the latest price and price history together. It uses yfinance, a Python library that fetches historical stock data from Yahoo Finance.
- `GET /articles` lists news articles. You can filter by stock ticker. Use `GET /article/{article_slug}` to open one article.
- `GET /stocks/most-mentioned` powers the Discover table. StocksFeed ranks S&P 500 stocks by the number of distinct articles that mention them over the past 24 hours. You can request all companies or a single sector.

For news, the server makes HTTP requests to the API behind [StocksFeed](https://stocksfeed.benollomo.com/), an earlier project of mine. If we need our own article fetcher for the datathon, we can replace the StocksFeed integration and keep the same routes for the dashboard.

See [how the dashboard, API, and database work together](../ARCHITECTURE.md).

## Run locally

Use Python 3.12. From this directory, copy `.env.example` to `.env` on first setup. It includes the StocksFeed API address in `STOCKSFEED_BASE_URL`.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Open [Swagger UI](http://localhost:8000/docs) or request a stock directly.

```sh
curl 'http://localhost:8000/stock/AAPL/history?period=1mo'
```

The response contains the latest Yahoo regular-market price in
`history.ticker.regularMarketPrice` and a list of candles in `history.candles`.
Each candle has `time`, `Open`, `High`, `Low`, `Close`, and `Volume`.
Candle times and the quote's `regularMarketTime` are Unix seconds.

| Period | Candle interval |
| --- | --- |
| `1d` (default), `5d` | 1 minute |
| `1mo`, `3mo`, `6mo`, `ytd`, `1y` | 1 hour |
| `3y`, `5y` | 1 day |

## Layout

- `app/main.py` creates the FastAPI app and registers feature routers.
- `app/modules/stocks/` owns the stock routes and their request and response types.
- `app/integrations/yahoo/service.py` fetches Yahoo data and converts it into a quote and candles.

Add new features under `app/modules/` and register their routers in `app/main.py`.

## StocksFeedAI articles

To fetch the latest articles for a stock or look up one article by its slug:

```sh
curl 'http://localhost:8000/articles?tickers=NVDA&limit=10'
curl 'http://localhost:8000/article/your-article-slug'
```

The list accepts `search`, comma-separated `tickers` and `sectors`, `sentiment`,
`hours` (1–720), `only_with_tickers` (default true), and `limit` (1–500, default 20).
A successful lookup with no matches returns an empty list or a null article.
Upstream failures return HTTP 502.

`GET /stocks/most-mentioned?sector=Technology&limit=10` returns S&P 500
companies ranked by distinct article URLs collected over the past 24 hours.
Omit `sector` for all sectors. The response includes the available company
sectors and the ranking’s UTC cutoff time.
