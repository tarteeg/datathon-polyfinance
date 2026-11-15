# Datathon PolyFinances 2026: AlphaForge AI

Team project for the PolyFinances 2026 Datathon, organized with National Bank and powered by AWS. The AlphaForge AI challenge asks teams to build a tool that uses generative AI, agents, and public financial data to inform an investment decision, based on three fictional personas: Prudent, Balanced, and Bold.

> The Next.js dashboard and the FastAPI API are in place. The AlphaForge AI features described in the planned approach are still to be built.

![PolyFinances AlphaForge News & Geopolitical Intelligence page, with the simulated portfolio in the sidebar and recent articles ranked by priority](docs/images/news-geopolitical-intelligence.png)

## Challenge constraints

- Simulation only: no real transactions, and the tool does not present itself as personalized financial advice.
- Process over performance: the jury rewards a credible, well-demonstrated process, not the best past return.
- Traceability: every data point cites its source, date, and currency, and facts, assumptions, and scenarios are kept distinct.

The official challenge statement is authoritative and may be clarified by the organizers on site.

## Planned approach

The code computes, the model explains. Returns, volatility, and correlations are computed with pandas, then a language model puts them in context using those figures. We use adjusted prices (`adj_close`) and avoid look-ahead bias (publication dates rather than quarter-end dates). The exact decision to inform and the comparison of two personas are still to be defined.

## Envisioned tech stack

- Amazon Bedrock to call models (Montréal region available)
- Strands Agents (Python) for the agent and its calculation tools
- Amazon SageMaker AI (JupyterLab) or Kiro for analysis
- pandas, NumPy, scikit-learn

The team AWS account is activated on November 14, 2026 and deleted at the end of the day on November 16. The code must be on GitHub before it expires.

## Getting started

1. Start the [FastAPI server](backend-server/README.md).
2. In another terminal, follow the [dashboard guide](frontend-dashboard/README.md), then open the [local dashboard](http://localhost:3000) and create an account or sign in.

The dashboard, based on [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard), lets you track a simulated portfolio, view a stock's prices and news, and spot the S&P 500 stocks most cited in articles from the last 24 hours. Settings are available by clicking your name in the sidebar.

The API fetches prices from Yahoo Finance with yfinance and news from [StocksFeed](https://stocksfeed.benollomo.com/). Amazon Aurora PostgreSQL stores accounts, sessions, and portfolio positions. See the [architecture guide](ARCHITECTURE.md) to follow the exchanges between services.

The [challenge report](DATATHON-CHALLENGE-REPORT.md) and the [AWS workshop notes](POLYFINANCES-WORKSHOP.md) document the project context.

## Team and license

Team members:

- Sami Mostfa
- Pacifique Uwamukiza
- Benjamin Ollomo
- Mohamed Oubagha
