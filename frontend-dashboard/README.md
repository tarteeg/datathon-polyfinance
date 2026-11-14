# Frontend dashboard

I forked [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard), a Next.js admin dashboard built with shadcn/ui. The stock and portfolio features are what I added for the datathon.

- Sign up or sign in with your email and password. Each account has its own portfolio.
- Search for an S&P 500 stock and add it to your portfolio. You can leave the number of shares blank or edit it later on Home.
- Open a stock to see its current price, change the period on its price chart, and read related news.
- On Home, use the Discover table to see which stocks appear most often in the news. It counts distinct articles from the past 24 hours, and you can filter by company sector.
- Open Finance chat in the sidebar for general finance Q&A. Expand Finance chat in the sidebar to start a chat or search saved threads grouped by date. Each thread has a link you can reopen.
- Click your name in the sidebar or the settings button in the header to change your name, password, or dashboard preferences.

The other dashboards, including CRM, Finance, and Analytics, are examples from Studio Admin. We can borrow layouts and components from them during the datathon, then remove the example pages we no longer need.

See [how the dashboard, API, and database work together](../ARCHITECTURE.md).

## Run locally

From this directory, install the dependencies with `npm install`. For a fresh checkout, copy `.env.example` to `.env.local`. Follow the [authentication setup](docs/authentication.md#local-setup) to configure Better Auth and connect to an existing Amazon Aurora PostgreSQL database. Set `BACKEND_API_URL` to the address of the [FastAPI server](../backend-server/README.md), usually `http://127.0.0.1:8000`.

On a fresh database, create the account, portfolio, and chat tables:

```sh
npm run auth:migrate
npm run portfolio:migrate
npm run chat:migrate
```

Start the dashboard with `npm run dev` and open [localhost:3000](http://localhost:3000).

## Finance chat setup

Set `CHAT_API_KEY` to the same server-side value as FastAPI and configure `BACKEND_API_URL` to reach it. Follow the [backend chat setup](../backend-server/README.md#finance-chat) for Bedrock configuration. Existing installations should rerun `npm run chat:migrate` to add chart, news, and stock snapshots and migrate any older single-conversation history.

Select **Explain this chart** on a stock page to save its current chart in a new conversation, then choose **Show related news** for recent coverage. Open **Finance chat** after signing in. The most recently active thread opens first. New chats use the first question as their title. Each request sends up to ten completed exchanges from the selected thread and the new question to Bedrock.

Ask Finance chat for recent news about a company, ticker, topic, or the broader market. News replies link to original publishers. Follow-ups can refer to stories by number after reopening the thread.

Ask for a company’s latest quote or performance over a supported period, then ask follow-ups about the figures in the same thread. Stock replies cite Yahoo Finance and include the quote timestamp when available.
