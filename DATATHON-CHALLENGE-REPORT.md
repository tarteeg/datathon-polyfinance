# AlphaForge AI | PolyFinances Datathon 2026 team report

**The challenge:** Build a working agent that uses public financial data to help a fictional investor understand a specific investment decision. A user should be able to see what the agent checked, how the result changes with their circumstances, and what evidence supports the conclusion. National Bank, AWS, and PolyFinances leave the choice of assets, use case, models, and most of the architecture to the team. (Slides 5785–5786, 5795.)

**Eligibility:** AWS must make a real, demonstrable contribution to the working solution. The presenter specified at least one AWS service. A project without effective integration is ineligible for final evaluation. AWS integration quality also carries **15% of the score**. The workshop tutorials are optional. (Slides 5790 and 5793, presentation at 09:58.)

**Submission:** The workshop lists **Sunday, November 15, 2026 at 11:59 p.m.** for the GitHub repository and application. The presentation specifies four deliverables: **prototype with code, video of about five minutes, technical documentation, and a one-page brief**. Prepare all four for hand-in. The supplied materials do not specify a separate upload destination or deadline for the video, documentation, or one-pager. [Workshop schedule](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop)

## Schedule and preservation

| When in 2026 | Event |
|---|---|
| Sat, Nov 14, morning | Team AWS accounts open. |
| Sat, Nov 14, noon | Datathon begins. |
| Sun, Nov 15, 4:00 p.m. | On-site event ends. |
| Sun, Nov 15, 11:59 p.m. | GitHub and application submission deadline. |
| Mon, Nov 16 | The workshop cleanup guide gives **1:59 p.m.** for permanent account and data deletion. The dashboard’s displayed start plus 72-hour duration implies **11:30 a.m.** on the same clock. |

The workshop schedule omits an explicit time zone. Use Sunday’s hand-in as the team’s export target. Save the demo recording, code, notebooks, permitted data, prompts, tool definitions, and AWS configuration outside the temporary account. A file copied into CloudShell still lives inside the event environment. [Workshop schedule and dashboard notes](POLYFINANCES-WORKSHOP.md) · [Cleanup guide](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/90-cleanup)

## What the judges need to see

The organizers offer several valid use cases: compare assets, examine scenarios, explain risk, propose a fictional allocation, or build another defensible decision aid. One asset can suffice if it answers the question. Historical portfolio performance has no standalone scoring category. The rubric rewards what a person can learn from the result, the quality of the evidence, and the team’s ability to demonstrate it. (Slides 5785–5786 and 5793.)

| Criterion | Weight | What the judges assess | Suggested evidence from your demo |
|---|---:|---|---|
| Solution | 20% | Relevance, innovation, creativity, working prototype | State the decision in one sentence. Run the case and show what the user can now understand. |
| Agentic design | 20% | Architecture and explainability | Show which tool the agent called, what came back, and which check affected the answer. |
| Data | 20% | Rigor, validation, visualization | Trace one figure from a dated source through a calculation to a labeled chart. Show a check that could catch an error. |
| UX/UI | 10% | Intuitiveness, ergonomics, clarity | Let a first-time user switch profiles and identify the changed constraint without narration. |
| AWS | 15% | Quality of integration | Run the feature that depends on AWS. Identify its input, output, and place in the architecture. |
| Pitch | 15% | Presentation, business value, marketing | Name the intended user, the decision they struggle with, and why they would use the tool again. |

## The three personas are tests of behavior

The workshop describes broad risk categories. The presentation gives each fictional investor a name, an investment horizon, and a tension that the system must handle. The years below are **horizons**, not investing experience. The organizers recommend demonstrating **at least two contrasting situations**. Designing for all three gives the team a way to check whether the underlying logic generalizes. (Slide 5787, presentation 00:21–03:44.)

| Persona | Situation from the slide | What a convincing result would show |
|---|---|---|
| **Amira, 26** | High risk tolerance, **15+ years**. Seeks growth, emerging technologies, and cryptoassets while retaining diversification. | If a proposed position duplicates exposure she already has, quantify the concentration and explain why diversification still matters. |
| **Mateo, 41** | Moderate risk, **8–12 years**. Wants a balance of growth and stability and has explicit environmental, social, and governance (ESG) preferences. | Identify the relevant ESG criterion and evidence. If the necessary disclosure is missing, say which part of the comparison remains unresolved. |
| **Robert, 59** | Low-to-moderate risk, **3–5 years**. Prioritizes capital preservation and stability, with occasional interest in a widely publicized opportunity. | Acknowledge why the opportunity caught his attention, then explain any conflict between its downside and his time horizon in ordinary language. |

**A useful comparison:** Keep the asset, observation date, and market data fixed while switching personas. The historical facts should stay the same. Show which constraint changes the interpretation. This makes adaptation visible and prevents the model from inventing different market histories to justify different answers.

## What “agentic” and “self-explaining” mean here

The slide explicitly allows one agent, several agents, or specialized agents. The speaker also suggested a debate agent as one possible design. Whichever design the team chooses, it should be able to explain why each agent exists, what it can do, and how its output helps the user. (Slide 5788, presentation 04:33–06:45.)

| Organizer’s term | Observable behavior |
|---|---|
| **Mobiliser** | Select and retrieve the relevant public data, tools, models, or search results. |
| **Coordonner** | Sequence tasks and checks. For example, check data coverage before comparing two assets. |
| **Adapter** | Use the investor’s goals, horizon, preferences, and constraints to decide what evidence matters. |
| **Expliquer** | Identify the sources, assumptions, factors, uncertainty, and limits behind the conclusion. |

A feasible implementation is one Bedrock-backed agent with tools for fetching dated observations and running deterministic calculations. Let code compute returns, drawdowns, or exposure. Give the model the computed values and source references to explain. Record the actual tool calls and results so the explanation can be checked against the run. Use bounded retries and a stopping condition. A short record of observable actions is enough to explain what happened. [Agent workshop](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents)

## Data choices and responsible use

The starter dataset is optional. Teams may supplement or replace it if they document their choices. For each input, answer four questions: **Why does it matter to this decision? Where did it come from? How was it transformed? What can it establish?** Record the source, observation date, publication date where relevant, currency or unit, and coverage gaps. (Slide 5789, presentation 07:27–09:33.)

| Evidence the decision needs | Candidate sources in the workshop | Common issue to address |
|---|---|---|
| Market prices, volumes, returns, dividends, splits | Yahoo Finance via yfinance | Document adjusted versus unadjusted prices, align observation dates, and check redistribution rights. |
| Revenue, earnings, debt, cash, issuer events | SEC EDGAR, SEDAR+, investor-relations reports | Use the date the filing became public when recreating a historical decision. |
| Portfolio concentration, sector overlap, fees | ETF issuer holdings and fact sheets | Identify the holdings date and any undisclosed portion before making an overlap claim. |
| Rates, inflation, employment, FX | Bank of Canada Valet, FRED, Statistics Canada | Align currencies, publication lags, and business-day calendars before comparing series. |
| News, ESG, sector or crypto signals | Dated public articles, issuer disclosures, relevant public series | Define what the signal measures. A headline alone cannot establish causality or ESG alignment. |
| Investor constraints | Supplied fictional personas and clearly labeled scenario inputs | Distinguish an organizer-supplied preference from a threshold invented for the demo. |

The event allows **simulation only**. Exclude real transactions, brokerage connections, personalized financial advice, personal information, and confidential banking data. Label observed facts, assumptions, and fictional scenarios where the user sees the result. Surface important uncertainty and give concise, verifiable explanations. If the evidence is insufficient, identify the missing evidence. The presentation explicitly warns against inventing explanations after the fact. (Slide 5794, presentation 17:49–19:40.) [Financial data guide](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/50-datasets) · [Responsible-use rules](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/20-setup/10-responsible-use)

## A worked demo idea

**Illustrative team proposal.** “What changes if a fictional investor moves 10% of a diversified portfolio into a technology fund that is in the news?” This gives the agent a specific task and the user a decision with a visible consequence. The 10% is a scenario assumption. The team can substitute a different asset or question.

1. **Formulate.** Define the proposed change, the holding it would replace, the observation date, and the portfolio currency. State what the user should learn.
2. **Design.** Use dated holdings to calculate overlapping exposure. If the hypothetical portfolio starts with 20% in technology, the fund being reduced is 20% technology, and the incoming fund is 80% technology, shifting ten percentage points raises total technology exposure to **26%**. The arithmetic is 20% + 10% × (80% − 20%). These figures are fictional and can double as a test case.
3. **Contextualize.** Show Amira the growth exposure and concentration change. For Robert, show why a headline offers little evidence about capital preservation over three to five years. For Mateo, surface the relevant ESG disclosure and its coverage. Each answer should identify the constraint that drove it.
4. **Test.** Change the shift to 5% and expect exposure of 23% under the same assumptions. Remove a holdings file and verify that the app reports the missing input. Switch personas and verify that the calculated exposures stay fixed.
5. **Explain.** Display the before-and-after figure, source dates, the assumption that holdings stay fixed, and the limitation that sector weight alone cannot establish future losses. Let the user inspect the evidence behind the answer.

These five steps follow the organizers’ suggested method: formulate a useful question, design the agent’s role, contextualize, test sensitivity, and explain. The scenario and acceptance checks above are team suggestions. (Slide 5791.)

## Demonstrating AWS in a weekend prototype

Use the event region, **us-east-1**. For the example above, the app could send the calculated exposures, profile constraints, and source references to **Amazon Bedrock** and display the resulting explanation. During the demo, change one input and show the corresponding tool result and Bedrock-backed response. A short architecture diagram can identify exactly where that call occurs. The speaker invited teams to ask AWS mentors about access or service questions. (Slide 5790, presentation 09:58–11:12.)

Add private S3 storage if the app needs shared snapshots, Lambda if it needs a callable endpoint, or a Bedrock Knowledge Base if a conclusion depends on retrieving a passage from a filing. SageMaker and JupyterLab are available for exploratory analysis. The team should be able to justify each service, explain its access permissions, and show what it contributes. Keep credentials out of Git and use only data the team can lawfully redistribute. The existing directory links all 35 workshop pages, including the Bedrock first-call, Strands, Guardrails, data, and export guides. [Workshop directory](POLYFINANCES-WORKSHOP.md)

## The four deliverables

| Deliverable | What the organizer asks for | Practical completion check |
|---|---|---|
| **1. Prototype and code** | One complete, demonstrable use case with an accessible explanation. A repository and README covering dependencies, data, configuration, and reproduction. | A teammate follows the README from a clean checkout, runs the example, and finds its evidence. |
| **2. Video** | **About five minutes**, an indicative duration. Show the problem, agents’ roles, data, result, and explanation end to end. | Watch once without pausing. Can a viewer name the decision, identify AWS’s contribution, and explain why the second situation produced a different interpretation? |
| **3. Documentation** | Architecture, agents, methods, sources, assumptions, explainability, validation, limits, and improvements. | Follow one displayed claim back to its calculation and source. Document one actual validation result and one limitation. |
| **4. One-pager** | One page covering the problem, approach, originality, data, explainability, and user value. | Use the same case as the prototype. Include one result or image the reader can interpret without opening the app. |

Slide 5792 settles the recording’s unclear duration at 15:24. The four artifacts should tell the same story. Use the same asset, data date, persona assumptions, and result across them so the jury can compare what the team claims with what the app does.

**Suggested five-minute cut:** Spend 30 seconds on the user and decision, 90 seconds running the first case, 60 seconds switching persona, 60 seconds showing sources, calculations, and the AWS call, and the final minute on a sensitivity check, a limitation, and user value. Record the actual workflow while the temporary account is active.

## Final review before hand-in

- [ ] The prototype completes one investment analysis in simulation and shows the evidence behind it.
- [ ] AWS performs a demonstrable step. The team can explain why it chose that service.
- [ ] The demo shows contrasting situations and identifies the specific constraint that changed the interpretation.
- [ ] Each figure has a date, source, unit or currency, and reproducible calculation. Hypothetical inputs are labeled.
- [ ] At least one changed assumption and one missing-data case have been tried. The team can describe what happened.
- [ ] The repository, application, video, documentation, and one-pager are accessible to the intended judges. A teammate has tested the links.
- [ ] Code, configuration, prompts, and permitted data are backed up outside AWS. Restricted data has retrieval instructions where appropriate.

## Source notes

This report draws on the 11 supplied slide photos, the French presentation, and the previously reviewed workshop. Photo numbers refer to filenames: 5785–5786 cover the rationale and challenge, 5787 the personas, 5788 agents, 5789 data, 5790 AWS eligibility, 5791 the method, 5792 deliverables, 5793 the rubric, 5794 responsible use, and 5795 the organizers’ closing guidance. Slide text supplies the exact persona details, percentages, and video length where the automated transcript is unclear. The organizers’ full case and subsequent on-site instructions take precedence. [Timestamped French transcript](TRANSCRIPTION-2026-11-14.md) · [AWS workshop notes and source links](POLYFINANCES-WORKSHOP.md)
