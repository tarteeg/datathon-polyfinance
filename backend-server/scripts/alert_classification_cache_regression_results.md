# Alert classification + scan-cache regression results

- **PASS** | 1. Materially significant event, no quantified signal -> NOT tier 5 (not confirmable) | tier=4, classification=evidence_supported_hypothesis
- **PASS** | 2. Explicit quantified price reaction attributed to the event -> tier 5 (confirmable) | tier=5, classification=verified_fact
- **PASS** | 3. Routine earnings-beat article -> dismissed_insufficient_evidence | classification=dismissed_insufficient_evidence
- **PASS** | 4. Regulatory direct match unaffected by the news-specific tier gate | classification=verified_fact, has_tier_field=False
- **PASS** | 5. A failed refresh preserves the last successful result and timestamp | status=error, result preserved=True
- **PASS** | 6. A scan-in-progress marker preserves the prior result while status flips to 'scanning' | status=scanning, result preserved=True
