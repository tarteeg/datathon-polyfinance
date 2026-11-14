# Alert verification regression results

Real output from `scripts/test_alert_verification_regression.py`, run live against real filings, a real Bedrock client, and the real (now cleaned-up) dedup table on 2026-11-14.


## Summary

| Case | Passed | Latency |
|---|---|---|
| 1. AMD article, generic 'semiconductor' overlap with AAPL | PASS | 3.26s |
| 2. Real NVDA/TSMC supplier dependency retained | PASS | 0.07s |
| 3. AMD/NVIDIA competitor relationship, no price-direction claim | PASS | 3.10s |
| 4. Generic geography word 'Taiwan' alone is insufficient | PASS | 2.56s |
| 5. Duplicate scan does not re-alert (dedup table) | PASS | 1.72s |

## Detail

### 1. AMD article, generic 'semiconductor' overlap with AAPL
- Query/case: Semiconductor Stocks Rally as AMD Beats Earnings Estimates
- Expected: No confirmed alert for AAPL
- Actual: AAPL matches found: 1, classifications: ['unverified_possibility'], confirmed: 0
- Passed: True
- Detail: [{'classification': 'unverified_possibility', 'reasoning': "The document discusses AMD beating earnings estimates, which caused a rally in semiconductor stocks broadly. AAPL is in the Electronic Computers sector and does use semiconductors (including its own Apple Silicon chips), so a general sector sentiment connection is plausible in principle. However, the evidence provided names only AMD specifically and uses the generic term 'semiconductor' — it does not name Apple, any specific Apple supplier, any specific chip or material shared between AMD and AAPL, or any concrete transmission mechanism linking AMD's earnings to AAPL's valuation. The shared trigger word 'semiconductor' is generic, and while AAPL operates in a related space, the evidence given does not establish a specific causal link beyond that generic overlap."}]

### 2. Real NVDA/TSMC supplier dependency retained
- Query/case: Taiwan Semiconductor Manufacturing (TSMC) Reports Record Quarterly Revenue on AI Chip Demand
- Expected: At least one confirmed alert (NVDA<->TSMC, a real known-supplier edge)
- Actual: matches: [('NVDA', 'TSMC', False)], confirmed: 1
- Passed: True
- Detail: [{'classification': 'evidence_supported_hypothesis', 'reasoning': "Literal match on a specific term ('TSMC'), not a generic category word."}]

### 3. AMD/NVIDIA competitor relationship, no price-direction claim
- Query/case: Nvidia Corporation posted strong quarterly results today as demand for artificial intelligence accelerators continued to grow amid robust customer orders.
- Expected: Competitor relationship recognized; recommendation contains no price-direction language
- Actual: competitor matches: 1, recommendation: "**AMD – Competitor Monitoring Alert (Simulation/Informational Only)**\n\nNvidia Corporation, a disclosed competitor of AMD in the AI accelerator and GPU market, has reported strong quarterly results driven by demand for artificial intelligence accelerators, per the matched document. Because this is a competitor relationship — not a supplier or material dependency — the existence of this news does not indicate any specific directional outcome for AMD's stock price in either direction. This is worth monitoring as context for AMD's positioning in the AI accelerator space; reviewing AMD's own disclosures, upcoming earnings commentary, and any analyst coverage addressing competitive dynamics in this segment would provide a more complete picture.\n\n*This alert is for simulation and informational purposes only and does not constitute investment advice or a recommendation to take any portfolio action.*"
- Passed: True

### 4. Generic geography word 'Taiwan' alone is insufficient
- Query/case: Taiwan's Economy Grows 3% Amid Strong Exports (vs AAPL, no other specific signal)
- Expected: unverified_possibility or dismissed_insufficient_evidence (never verified_fact/evidence_supported_hypothesis)
- Actual: dismissed_insufficient_evidence
- Passed: True
- Detail: {'classification': 'dismissed_insufficient_evidence', 'reasoning': "The document concerns Taiwan's macroeconomic export growth, and the only connection to AAPL identified in the filing evidence is that AAPL has a regional operations center in Taiwan supporting 'local administrative functions.' This is a generic administrative presence, not a specific supply chain, manufacturing, material, or named entity link that would transmit Taiwan's export-driven economic growth into a causal impact on AAPL's retail business. The shared word 'Taiwan' is the sole connector, and no specific causal transmission mechanism — such as a named supplier, component, or material dependency — is present in the evidence provided."}

### 5. Duplicate scan does not re-alert (dedup table)
- Query/case: filter_unseen called twice with identical (test-dedup-doc-001, test-user, NVDA)
- Expected: First call returns it as unseen; second call returns empty
- Actual: first=[('test-dedup-doc-001', 'test-user', 'NVDA')], second=[]
- Passed: True
