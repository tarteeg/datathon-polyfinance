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
| `mtd`, `1mo`, `3mo`, `6mo`, `ytd`, `1y` | 1 hour |
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

## Finance chat

`POST /chat` accepts the current question and up to ten previous exchanges from the signed-in dashboard. For stock-chart conversations the dashboard also supplies the saved chart figures in `chart`. FastAPI calls Bedrock Converse and returns an `answer`. Interactive chat uses `POST /chat/stream` with the same request body. It sends newline-delimited JSON text deltas followed by a completion record containing the source snapshots. The dashboard saves each completed exchange to Aurora.

Set `AWS_REGION` and `BEDROCK_MODEL_ID` in the backend environment to the region and model or inference profile you can invoke. Configure backend AWS credentials with `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` access or set a Bedrock API key in `AWS_BEARER_TOKEN_BEDROCK`. Generate a shared key with `openssl rand -hex 32` and set `CHAT_API_KEY` to that value in both apps’ server environments. The dashboard supplies it in the `X-Chat-Key` header.

When the dashboard supplies session-scoped holdings, Bedrock can request quantities, valuation or coverage of saved tickers through `get_my_portfolio`. Quotes are grouped by currency and stocks without a quantity are tracked separately. Run `npm run chat:migrate` in the dashboard to enable saved portfolio breakdowns.

For news questions, Bedrock can request multiple read-only StocksFeed searches per message. The response includes the numbered source list and a news snapshot. The dashboard can send that snapshot as `previous_news` when continuing a thread.

## Calculation tools

`app/modules/analysis/` adds six read-only tools to the finance chat. Bedrock chooses them; every figure comes from the pure functions in `calculations.py`.

| Tool | What it computes |
| --- | --- |
| `simulate_transfer` | Weights, sector exposure and concentration before and after moving a share of the whole portfolio from one holding to another |
| `sector_exposure` | Sector weights, with the unclassified share |
| `concentration` | Largest line, top-3 weight, Herfindahl index, effective number of lines |
| `risk_history` | Total and annualized return, annualized volatility, maximum drawdown with dates, per symbol and for a constant-weight portfolio |
| `check_data` | Whether price histories share dates and currency |
| `convert_currency` | Amounts converted with the latest Bank of Canada daily rate |

The user's own portfolio (`portfolio=mine`) is valued in CAD with the Bank of Canada rate. Sector shares come from Yahoo Finance; `risk_history` uses daily closes adjusted for splits and dividends. The tools need outbound HTTPS access to Yahoo Finance and `www.bankofcanada.ca`, and no new environment variable.

## Figure check

`app/modules/verification/` checks each reply after it streams. `/chat/stream` sends one more activity record, `verify_answer`, whose `output` holds the verdict (`verified`, `review`, `rejected` or `unverified`), the number of figures checked, the figures with no source and the figures computed from other figures. It needs no new environment variable and no model call. `POST /chat` does not run the check. The figures it matches come from the tool results of the same question, the question itself, and the saved `chart`, `previous_stock`, `previous_news` and `history` fields. A failure inside the check never blocks a reply.

Run the calculation and verification tests from this directory:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest tests
```
