# Portfolio/persona regression results

Real output from `scripts/test_portfolio_persona_regression.py`.

- PASS | 1. Scenario-shock calculator matches manual calculation | computed=-0.150000 expected=-0.150000
- PASS | 2. Equal-weight assumption is reflected in every persona's verdict text | verdicts mention the assumption: [True, True, True]
- PASS | 3. Three personas produce genuinely distinct assessments | distinct verdict texts=True, distinct violation sets=True (amira=2 violations, mateo=3, robert=4)
- PASS | 4. Robert's profile is challenged; Amira's exposure alone isn't auto-flagged the same way | robert.challenges_the_request=True, amira.challenges_the_request=False
- PASS | 5. Mateo's ESG evidence gap is disclosed, not silently assumed | esg_notes=["Mateo has an explicit ESG preference, but this investigation did not find ESG-relevant disclosure for NVDA, AMD. This is a real evidence gap, not an ESG judgment -- it should not be read as either a pass or a fail on Mateo's ESG criterion."]
- PASS | 6. Unrecognized exposure tier raises rather than silently defaulting | ValueError raised as expected

## Live end-to-end evidence (manually verified separately, not scripted here)

`POST /riskripple/investigate` with event="New export controls restrict advanced semiconductor chips to China", holdings=[NVDA, AMD], quantities={NVDA:15, AMD:10}:
- Real position weights from live prices: NVDA 31.4%, AMD 68.6%.
- Real annualized volatility: NVDA 47.3%, AMD 61.3%.
- Agent recorded both as `direct_verified` with real, specific 10-K evidence ($4.5B NVDA H20 charge, $800M AMD MI308 charge).
- One bounded follow-up question fired: asked whether TSMC's own filing discloses export-control constraints on wafer production; correctly classified `unresolved` (TSMC files Form 20-F, not indexed by the full-text search tool used) rather than inventing a finding.
- Same scenario, holdings=[NVDA, ABNB], no quantities given: weights correctly disclosed as an assumed 50/50 equal split; ABNB correctly classified `no_established_link` with reasoning that explicitly names unexamined indirect channels (cloud spend, Chinese tourism demand) rather than claiming zero exposure.
- Confirmed live against real SEC EDGAR data: ABNB's `Services-To Dwellings & Other Buildings` SIC classification is genuinely correct (SEC's own submissions data), not a pipeline bug -- a known quirk of the decades-old SIC coding scheme.
- Banned phrase "All evidence is in" no longer appears; replaced with "Investigation completed within the sources and tools available."
