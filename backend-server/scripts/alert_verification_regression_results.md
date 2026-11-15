# Alert verification regression results

Real output from `scripts/test_alert_verification_regression.py`, run live against real filings, a real Bedrock client, and the real (now cleaned-up) dedup table on 2026-11-14.


## Summary

| Case | Passed | Latency |
|---|---|---|
| 1. AMD article, generic 'semiconductor' overlap with AAPL | PASS | 3.24s |
| 2. Real NVDA/TSMC supplier dependency retained | PASS | 0.10s |
| 3. AMD/NVIDIA competitor relationship, no price-direction claim | PASS | 3.33s |
| 4. Generic geography word 'Taiwan' alone is insufficient | PASS | 2.64s |
| 5. Duplicate scan does not re-alert (dedup table) | PASS | 1.70s |

## Detail

### 1. AMD article, generic 'semiconductor' overlap with AAPL
- Query/case: Semiconductor Stocks Rally as AMD Beats Earnings Estimates
- Expected: No confirmed alert for AAPL
- Actual: AAPL matches found: 1, classifications: ['unverified_possibility'], confirmed: 0
- Passed: True
- Detail: [{'classification': 'unverified_possibility', 'reasoning': "The document discusses AMD beating earnings estimates, which triggered a rally in semiconductor stocks broadly. AAPL (Apple) is in the Electronic Computers sector and does use semiconductors (including its own custom silicon), so a sector-wide sentiment lift is plausible in principle. However, the evidence given names only AMD and the generic term 'semiconductor' — it does not name Apple, any specific Apple supplier, any shared material, or any direct causal mechanism connecting AMD's earnings to AAPL's valuation. The connection remains a plausible but unverified sector-sentiment hypothesis, not something the provided evidence specifically establishes."}]

### 2. Real NVDA/TSMC supplier dependency retained
- Query/case: Taiwan Semiconductor Manufacturing (TSMC) Reports Record Quarterly Revenue on AI Chip Demand
- Expected: At least one confirmed alert (NVDA<->TSMC, a real known-supplier edge)
- Actual: matches: [('NVDA', 'TSMC', False)], confirmed: 1
- Passed: True
- Detail: [{'classification': 'evidence_supported_hypothesis', 'reasoning': "Literal match on a specific term ('TSMC'), not a generic category word."}]

### 3. AMD/NVIDIA competitor relationship, no price-direction claim
- Query/case: Nvidia Corporation posted strong quarterly results today as demand for artificial intelligence accelerators continued to grow amid robust customer orders.
- Expected: Competitor relationship recognized; recommendation contains no price-direction language
- Actual: competitor matches: 1, recommendation: "**AMD – Competitor Activity Alert (Informational/Simulation Only)**\n\nNvidia Corporation, a disclosed competitor of AMD in the semiconductors space, has reported strong quarterly results driven by demand for AI accelerators, per the matched document. Because this is a competitor relationship — not a supplier or material dependency — the existence of this news does not, on its own, indicate any particular directional outcome for AMD's business or stock price. It is worth monitoring how broader AI accelerator demand trends, as described in Nvidia's results, may be shaping the competitive landscape that AMD also operates within, and reviewing any relevant AMD filings or disclosures for context on its own AI-related product positioning.\n\n*This alert is for informational and simulation purposes only. Nothing here constitutes investment advice or a recommendation to take any portfolio action.*"
- Passed: True

### 4. Generic geography word 'Taiwan' alone is insufficient
- Query/case: Taiwan's Economy Grows 3% Amid Strong Exports (vs AAPL, no other specific signal)
- Expected: unverified_possibility or dismissed_insufficient_evidence (never verified_fact/evidence_supported_hypothesis)
- Actual: dismissed_insufficient_evidence
- Passed: True
- Detail: {'classification': 'dismissed_insufficient_evidence', 'reasoning': "The document concerns Taiwan's macroeconomic export growth, and the only connection to AAPL identified in the filing evidence is that AAPL has a regional operations center in Taiwan supporting 'local administrative functions.' This is a generic administrative presence, not a specific supply chain, manufacturing, export, or revenue mechanism that would transmit Taiwan's export-driven economic growth to AAPL's performance. The shared word 'Taiwan' is the sole link, and no specific named supplier, material, contract, or causal mechanism is identified in the evidence that would connect Taiwan's export economy story to this holding's financials. The connection is coincidental use of a geographic term."}

### 5. Duplicate scan does not re-alert (dedup table)
- Query/case: filter_unseen called twice with identical (test-dedup-doc-001, test-user, NVDA)
- Expected: First call returns it as unseen; second call returns empty
- Actual: first=[('test-dedup-doc-001', 'test-user', 'NVDA')], second=[]
- Passed: True
