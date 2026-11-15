# Datathon PolyFinances 2026: AlphaForge AI

Team project for the PolyFinances 2026 Datathon, organized with National Bank and powered by AWS. The AlphaForge AI challenge asks teams to build a tool that uses generative AI, agents, and public financial data to inform an investment decision, based on three fictional personas: Prudent, Balanced, and Bold.

> The Next.js dashboard, the FastAPI API, the finance chat, and the RiskRipple alerts are in place. BreakPoint AI is available from the dashboard sidebar.

![PolyFinances AlphaForge News & Geopolitical Intelligence page, with the simulated portfolio in the sidebar and recent articles ranked by priority](docs/images/news-geopolitical-intelligence.png)

## Tech stack

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, and shadcn/ui, based on Studio Admin. Recharts for charts and OpenUI to render chat replies.
- Authentication: Better Auth.
- Database: Amazon Aurora PostgreSQL (accounts, sessions, portfolios, chat history).
- Backend: FastAPI and Uvicorn (Python 3.12).
- AI: Amazon Bedrock (Converse and ConverseStream, knowledge base for RiskRipple) and Strands Agents for the RiskRipple agents.
- Computation: pandas, NumPy, SciPy, and NetworkX.
- Data: Yahoo Finance (yfinance), StocksFeed, and the Bank of Canada Valet API.

The team AWS account is activated on November 14, 2026 and deleted at the end of the day on November 16. The code must be on GitHub before it expires.

## Installation guide

### Prerequisites

- Git
- Python 3.12
- Node.js and npm (a version compatible with Next.js 16)
- An existing PostgreSQL database (Amazon Aurora PostgreSQL) and its RDS CA certificate, for accounts, sessions, portfolios, and conversations
- An AWS account with access to Amazon Bedrock, for the finance chat (AWS credentials or a Bedrock API key)
- OpenSSL, to generate the secret keys

### 1. Clone the repository

```sh
git clone <repository-url>
cd datathon-polyfinance
```

### 2. Generate the shared keys

Two values must be created once:

```sh
openssl rand -hex 32      # CHAT_API_KEY, identical in both applications
openssl rand -base64 32   # BETTER_AUTH_SECRET, dashboard only
```

### 3. Install the FastAPI server

From `backend-server/`:

```sh
cd backend-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

| Variable | Purpose |
| --- | --- |
| `STOCKSFEED_BASE_URL` | StocksFeed API address (default value provided) |
| `AWS_REGION`, `BEDROCK_MODEL_ID` | Bedrock region and model used by the chat |
| `AWS_BEARER_TOKEN_BEDROCK` | Optional: Bedrock API key instead of AWS credentials |
| `CHAT_API_KEY` | Key shared with the dashboard |
| `DATABASE_*` | Same connection values as the dashboard, required by the RiskRipple analyses |

Start the server:

```sh
python main.py
```

Check it with the [Swagger documentation](http://localhost:8000/docs) or `curl 'http://localhost:8000/stock/AAPL/history?period=1mo'`.

### 4. Install the dashboard

In a second terminal, from `frontend-dashboard/`:

```sh
cd frontend-dashboard
npm install
cp .env.example .env.local
```

Fill in `.env.local`:

| Variable | Purpose |
| --- | --- |
| `BETTER_AUTH_URL` | `http://localhost:3000` locally |
| `BETTER_AUTH_SECRET` | Secret generated in step 2 |
| `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_CA_CERT` | Connection to the existing PostgreSQL database |
| `BACKEND_API_URL` | FastAPI server address, `http://127.0.0.1:8000` |
| `CHAT_API_KEY` | Same value as in `backend-server/.env` |

On an empty database, create the tables, then start the dashboard:

```sh
npm run auth:migrate
npm run portfolio:migrate
npm run chat:migrate
npm run dev
```

Open the [local dashboard](http://localhost:3000) and create an account or sign in.

Keep credentials in `.env` and `.env.local`, which must not be committed. For more details, see the [server guide](backend-server/README.md) and the [dashboard guide](frontend-dashboard/README.md).

### Troubleshooting

- The chat returns an authentication error: check that `CHAT_API_KEY` is identical in both environment files, then restart both servers.
- Bedrock error: check `AWS_REGION`, `BEDROCK_MODEL_ID`, and the `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions.
- Database connection error: check the Aurora writer endpoint (no protocol or port), the database name, and `DATABASE_CA_CERT`.
- Prices or news do not appear: the server needs outbound HTTPS access to Yahoo Finance and StocksFeed.

## Features

The dashboard, based on [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard), lets you track a simulated portfolio, view a stock's prices and news, spot the S&P 500 stocks most cited in articles from the last 24 hours, and ask questions to the finance chat. The chat relies on Amazon Bedrock, calculation tools (sector exposure, concentration, risk history, currency conversion), and a check of the figures in each reply. BreakPoint AI determines how far an ETF must fall to reach a loss limit and compares the scenario with the historical drawdown of a SPY/TLT portfolio in 2022. A RiskRipple page analyzes the portfolio's exposure to news and regulatory alerts. Settings are available by clicking your name in the sidebar.

The API fetches prices from Yahoo Finance with yfinance and news from [StocksFeed](https://stocksfeed.benollomo.com/). Amazon Aurora PostgreSQL stores accounts, sessions, and portfolio positions. See the [architecture guide](ARCHITECTURE.md) to follow the exchanges between services.

## Team and license

Team members:

- Sami Mostfa
- Pacifique Uwamukiza
- Benjamin Ollomo
- Mohamed Oubagha
