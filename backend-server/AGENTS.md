# Working on the FastAPI server

Run commands from `backend-server/`. Follow [the README](README.md#run-locally) to set up the Python 3.12 environment, then start the server with `python main.py`. Open [the local API docs](http://localhost:8000/docs) to try a route.

## Where to make a change

- Put routes under `app/modules/<feature>/routes.py` and keep request and response schemas alongside them. Register new routers in `app/main.py`. The top-level `main.py` starts the development server.
- For prices and history, use `app/integrations/yahoo/service.py`. It calls yfinance and returns the current quote and historical candles together through `GET /stock/{ticker}/history`.
- For article lists, individual articles, and most-mentioned stocks, use `app/integrations/stocksfeed/service.py`. It calls the StocksFeed API over HTTP. If the project starts collecting its own articles, change the data source here and preserve the routes the dashboard calls.
- Document new environment variables in `.env.example`. Keep local values in `.env`. Set `STOCKSFEED_BASE_URL` to the API origin shown in the example.

## Checking a route change

Check how the dashboard reads the fields you change. For example, `../frontend-dashboard/src/server/stock-history.ts` expects the price in `history.ticker.regularMarketPrice` and chart data in `history.candles`. Each candle uses Unix seconds for `time` and a capital C in `Close`. Try `/stock/AAPL/history?period=1mo` in the local API docs or browser to check the response.
