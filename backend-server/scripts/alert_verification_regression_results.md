# Alert verification regression results

Real output from `scripts/test_alert_verification_regression.py`, run live against real filings, a real Bedrock client, and the real (now cleaned-up) dedup table on 2026-11-14.


## Summary

| Case | Passed | Latency |
|---|---|---|
| 1. AMD article, generic 'semiconductor' overlap with AAPL | PASS | 2.87s |
| 2. Real NVDA/TSMC supplier dependency retained | PASS | 0.10s |
| 3. AMD/NVIDIA competitor relationship, no price-direction claim | PASS | 2.71s |
| 4. Generic geography word 'Taiwan' alone is insufficient | PASS | 2.65s |
| 5. Duplicate scan does not re-alert (dedup table) | PASS | 1.68s |

## Detail

### 1. AMD article, generic 'semiconductor' overlap with AAPL
- Query/case: Semiconductor Stocks Rally as AMD Beats Earnings Estimates
- Expected: No confirmed alert for AAPL
- Actual: AAPL matches found: 1, classifications: ['unverified_possibility'], confirmed: 0
- Passed: True
- Detail: [{'classification': 'unverified_possibility', 'reasoning': "The document discusses AMD beating earnings estimates, which triggered a rally in semiconductor stocks broadly. AAPL is in the Electronic Computers sector and is a major consumer of semiconductors, so a sector-wide rally could plausibly affect it. However, the evidence given names only AMD specifically — there is no mention of Apple, its suppliers, or any specific transmission mechanism connecting AMD's earnings to AAPL's valuation. The shared word 'semiconductor' is generic, and while a plausible indirect connection exists (sector sentiment, supply chain), the evidence provided does not establish any specific named link between AMD's earnings and AAPL."}]

### 2. Real NVDA/TSMC supplier dependency retained
- Query/case: Taiwan Semiconductor Manufacturing (TSMC) Reports Record Quarterly Revenue on AI Chip Demand
- Expected: At least one confirmed alert (NVDA<->TSMC, a real known-supplier edge)
- Actual: matches: [('NVDA', 'TSMC', False)], confirmed: 1
- Passed: True
- Detail: [{'classification': 'evidence_supported_hypothesis', 'reasoning': "Literal match on a specific term ('TSMC'), not a generic category word."}]

### 3. AMD/NVIDIA competitor relationship, no price-direction claim
- Query/case: Nvidia Corporation posted strong quarterly results today as demand for artificial intelligence accelerators continued to grow amid robust customer orders.
- Expected: Competitor relationship recognized; recommendation contains no price-direction language
- Actual: competitor matches: 1, recommendation: "**AMD – Competitor Monitoring Alert (Simulation/Informational Only)**\n\nNvidia Corporation, a disclosed competitor of AMD in the AI accelerator and GPU market, has reported strong quarterly results driven by demand for AI accelerators, as noted in the evidence snippet. Because this is a competitor relationship — not a supplier or material dependency — the existence of this news does not indicate any specific directional outcome for AMD's stock price in either direction. Portfolio holders may wish to monitor further developments in the AI accelerator space and review their overall sector concentration in semiconductor and AI hardware holdings, as this document may provide broader context about the competitive landscape AMD operates within."
- Passed: True

### 4. Generic geography word 'Taiwan' alone is insufficient
- Query/case: Taiwan's Economy Grows 3% Amid Strong Exports (vs AAPL, no other specific signal)
- Expected: unverified_possibility or dismissed_insufficient_evidence (never verified_fact/evidence_supported_hypothesis)
- Actual: dismissed_insufficient_evidence
- Passed: True
- Detail: {'classification': 'dismissed_insufficient_evidence', 'reasoning': "The document concerns Taiwan's macroeconomic export growth, and the only connection to AAPL identified in the filing evidence is that AAPL has a regional operations center in Taiwan supporting 'local administrative functions.' This is an administrative back-office presence, not a manufacturing, supply chain, or export-related link. The filing evidence names no specific supplier, material, named act, or mechanism that would transmit Taiwan's export-driven economic growth to AAPL's retail operations. The shared word 'Taiwan' is the sole trigger, and the filing snippet describes only a generic administrative function with no plausible causal transmission mechanism to the document's subject matter."}

### 5. Duplicate scan does not re-alert (dedup table)
- Query/case: filter_unseen called twice with identical (test-dedup-doc-001, test-user, NVDA)
- Expected: First call returns it as unseen; second call returns empty
- Actual: first=[('test-dedup-doc-001', 'test-user', 'NVDA')], second=[]
- Passed: True
