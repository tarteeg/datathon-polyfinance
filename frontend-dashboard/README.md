# Frontend dashboard

I forked [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard), a Next.js admin dashboard built with shadcn/ui. The stock and portfolio features are what I added for the datathon.

- Sign up or sign in with your email and password. Each account has its own portfolio.
- Search for an S&P 500 stock and add it to your portfolio. You can leave the number of shares blank or edit it later on Home.
- Open a stock to see its current price, change the period on its price chart, and read related news.
- On Home, use the Discover table to see which stocks appear most often in the news. It counts distinct articles from the past 24 hours, and you can filter by company sector.
- Click your name in the sidebar or the settings button in the header to change your name, password, or dashboard preferences.

The other dashboards, including CRM, Finance, and Analytics, are examples from Studio Admin. We can borrow layouts and components from them during the datathon, then remove the example pages we no longer need.

See [how the dashboard, API, and database work together](../ARCHITECTURE.md).

## Run locally

From this directory, install the dependencies with `npm install`. For a fresh checkout, copy `.env.example` to `.env.local`. Follow the [authentication setup](docs/authentication.md#local-setup) to configure Better Auth and connect to an existing Amazon Aurora PostgreSQL database. Set `BACKEND_API_URL` to the address of the [FastAPI server](../backend-server/README.md), usually `http://127.0.0.1:8000`.

On a fresh database, create the account and portfolio tables:

```sh
npm run auth:migrate
npm run portfolio:migrate
```

Start the dashboard with `npm run dev` and open [localhost:3000](http://localhost:3000).
