# Datathon PolyFinances 2026 · AlphaForge AI

## Challenge requirements

Build an original tool that uses AI and public financial data to support an investment analysis or decision for three fictional investor profiles: **Prudent**, **Équilibré**, and **Audacieux**. National Bank proposed the challenge. The organizers’ official brief and on-site updates take precedence over the AWS workshop. [Workshop brief](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop) · [Organizer’s event site](https://polyfinances.ca/datathon)

- **Assets and data.** Choose the assets and explain their relevance. One instrument is enough for a well-defined question. No particular dataset is required. Use fictional investor information and respect each data source’s license.
- **Simulation only.** Keep real transactions, brokerage connections, confidential client data, and personalized financial advice out of the prototype.
- **Traceability.** Cite the source, date, and currency of each financial observation. Distinguish facts, assumptions, and scenarios.
- **Judging and demo guidance.** The jury values a credible method, a useful result, and a convincing demonstration. The workshop suggests calculating returns, volatility, and correlations in code, then asking the model to explain the results. Showing the same decision for two personas is a demo suggestion. The challenge names all three.

## Deadlines

**Submit both the GitHub repository and the application by Sunday, November 15, 2026 at 11:59 p.m.** The workshop lists these event times without an explicit time zone. [Workshop schedule](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop)

| Date | Time | Milestone |
| --- | --- | --- |
| Fri, Nov 6 | 2:00 p.m. | Online AWS workshop |
| Sat, Nov 14 | Morning | Team AWS accounts open |
| Sat, Nov 14 | Noon | Datathon begins |
| Sun, Nov 15 | 4:00 p.m. | On-site event ends |
| Sun, Nov 15 | 11:59 p.m. | GitHub repository and application due |
| Mon, Nov 16 | 1:59 p.m. | Account closure and permanent data deletion according to the workshop guide |

**Account cutoff discrepancy.** The dashboard lists a Nov 13 start at 11:30 a.m. and a 72-hour duration. On the same clock, that implies Nov 16 at 11:30 a.m. The cleanup guide explicitly gives 1:59 p.m. Exporting by Sunday’s submission deadline avoids relying on either Monday time. [Event dashboard](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR) · [Cleanup guide](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/90-cleanup)

## Team AWS environment

The dashboard lists Northern Virginia (`us-east-1`) as the accessible region, workshop level 200, and Amazon Bedrock and Amazon SageMaker as featured services. The team account is supplied for the event. The dashboard provides console access, temporary CLI credentials, and a private Kiro IDE link under the `kiro-ide-browser` stack. Open the IDE through the dashboard. The AWS tutorials are optional. [Event dashboard](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR)

## Workshop directory

All 35 French pages, in navigation order. Each link opens the corresponding page in the event workspace.

### Overview

- [Datathon PolyFinances 2026](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop) — Challenge brief, judging priorities, suggested demo, schedule, and account lifetime.

### Getting started

- [Commencer](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/20-setup) — Open the team console from an existing Workshop Studio session and select the event region.
- [Utilisation responsable](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/20-setup/10-responsible-use) — Use public or fictional data, keep infrastructure private, protect credentials, and bound agent calls.
- [SageMaker Unified Studio et notebook d’introduction](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/20-setup/20-sagemaker-unified-studio) — One teammate creates the shared domain. JupyterLab runs the starter notebook under the project execution role.

### AWS service references

- [Introduction à AWS](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions) — Map the project’s storage, analysis, model, and demo needs to AWS services.
- [Amazon Bedrock](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/5-bedrock) — Access foundation models through a common managed service.
- [Kiro](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/10-kiro) — Develop with an AI coding agent using requirements, a design, and implementation tasks.
- [Outils de développement](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/15-dev) — Choose where to write and run code and how the team will preserve its work.
- [Amazon Quick](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/20-quick) — Build business intelligence dashboards and interpret the QuickSight and Quick naming in related material.
- [AWS Lambda](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/25-lambda) — Expose a function so the demo can call code through a URL.
- [Amazon S3](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/30-s3) — Store input data, documents, and analysis outputs as objects.
- [AWS IAM](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/35-iam) — Use roles and permissions to control which services a user or notebook can access.
- [AWS Glue](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/80-glue) — Build and monitor extract, transform, and load jobs in Glue Studio.
- [Amazon Athena](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/25-instructions/85-athena) — Run SQL against files in S3 without provisioning a database.

### Command-line and SDK access

- [Accès AWS CLI et SDK](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/26-cli-sdk) — Access the team account from CloudShell, a local terminal, or an application using temporary credentials.

### Generative AI

- [L’IA générative sur AWS](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/30-genai) — Find the Bedrock guides for inference, safeguards, retrieval, and document extraction.
- [Votre premier appel de modèle](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/30-genai/10-first-call) — Make a first text-model request through the Converse API.
- [Choisir un modèle](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/30-genai/20-choosing-a-model) — Select a model and its inference profile. The workshop suggests trying a small model first.
- [Garde-fous](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/30-genai/30-guardrails) — Filter inputs and outputs to help enforce the prototype’s financial-advice and data boundaries.
- [Bases de connaissances et RAG](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/30-genai/40-knowledge-bases) — Retrieve relevant passages from source documents so answers can cite supporting evidence.
- [Data Automation](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/30-genai/50-data-automation) — Extract structured JSON from documents, images, audio, and video for downstream analysis.

### Agents

- [Construire des agents](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents) — Work through a financial example in which tools retrieve prices and compute ETF risk metrics.
- [Fonctionnement des agents](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents/10-concepts) — Understand the model/tool loop and why it needs a stopping condition.
- [Strands Agents](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents/20-strands) — Build an agent with the open-source Strands SDK and a Bedrock model.
- [Amazon Bedrock AgentCore](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents/30-agentcore) — Explore managed services around the agent and decide which capabilities the project needs.
- [MCP](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents/40-mcp) — Connect agents to tools exposed by a Model Context Protocol server.

### Quick starts

- [Démarrages rapides](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/40-quickstarts) — Short setup guides for storage and coding assistants.
- [Bucket S3](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/40-quickstarts/40-s3bucket) — Create a private bucket for source data, reports, intermediate results, and exports.
- [Assistants de code IA](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/40-quickstarts/60-ai-coding-assistant) — Describe a prototype precisely and evaluate the code an assistant produces.
- [Kiro](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/40-quickstarts/60-ai-coding-assistant/10-kiro) — Turn a feature description into a specification and implementation tasks.
- [Claude Code sur Bedrock](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/40-quickstarts/60-ai-coding-assistant/20-claude-code) — Configure the terminal coding assistant to use the team’s Bedrock access.
- [Codex sur Bedrock](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/40-quickstarts/60-ai-coding-assistant/30-codex) — Configure Codex to use OpenAI models hosted on Bedrock through the team account.

### Data, export, and further resources

- [Données financières publiques](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/50-datasets) — Find public financial data, example symbols, suggested CSV schemas, and licensing guidance.
- [Nettoyage et exportation](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/90-cleanup) — Save code, notebooks, S3 data, prompts, tool definitions, and service configuration outside the temporary account.
- [Ressources](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/95-resources) — Find AWS Skill Builder and other learning material that remains accessible after the event.

## Financial data sources and export notes

| Source | Coverage and practical detail |
| --- | --- |
| Yahoo Finance via yfinance | Daily prices, dividends, and splits. Check redistribution rights before committing downloaded data. |
| Bank of Canada Valet API | CAD exchange rates, interest rates, and bond yields. JSON or CSV without a key. Match Canadian business days when joining FX and prices. |
| FRED and Statistics Canada | Macroeconomic series. Track publication dates as well as observation periods to avoid using information that was unavailable at the time. |
| SEC EDGAR and SEDAR+ | US and Canadian issuer filings. EDGAR offers XBRL financials and requires an identifying User-Agent. |
| ETF issuers | iShares Canada, Vanguard Canada, and State Street SPDR publish holdings and fund information. Record the holdings’ as-of date. |
| Company investor relations | Annual reports, earnings releases, and presentations can supply evidence for document retrieval. |
| Registry of Open Data on AWS | Public datasets in S3. The workshop flags that the listed AWS copy of GDELT has stopped updating. |

Example instruments include `RY.TO`, `SHOP.TO`, `XIU.TO`, `XBB.TO`, `SPY`, `TLT`, `GLD`, and `BTC-USD`. The suggested CSV layouts cover asset metadata, prices, corporate actions, fundamentals, fund holdings, and macro series. Use the files the project needs. When a license restricts redistribution, publish the retrieval script. [Dataset guide](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/50-datasets)

Push code to the team repository throughout the event. Export notebooks, permitted datasets, prompts, tool descriptions, guardrail settings, knowledge-base configuration, and a short architecture note. Files copied from S3 into CloudShell still need to reach a destination outside the event account. Keep credentials and local environment files out of the repository. [Export checklist](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/90-cleanup)
