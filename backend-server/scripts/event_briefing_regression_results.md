# Event briefing regression results

- PASS | 1. Exposure buckets sum to total portfolio weight, each holding counted once | direct=0.5 potential=0.3 no_link=0.2 total=1.000000
- PASS | 2. indirect_evidence_supported + unverified_possibility both land in potential_exposure_pct | potential=0.8 direct=0
- PASS | 3. affected_holdings excludes no_established_link, count matches list length | affected=['NVDA', 'AMD'] count=2
- PASS | 4a. Any direct_verified -> ESCALATE even at tiny weight | single direct_verified holding present
- PASS | 4b. Strongest tier indirect_evidence_supported (no direct_verified) -> REVIEW | no direct_verified, one indirect_evidence_supported
- PASS | 4c. Strongest tier unverified_possibility -> MONITOR | weakest non-zero tier only
- PASS | 4d. All holdings no_established_link -> MONITOR (a real negative result, not escalated) | every holding checked and cleared
- PASS | 5. Mixed 4-tier portfolio: direct=25%, potential=50% (B+C), no_link=25%, attention=ESCALATE | {'direct_exposure_pct': 0.25, 'potential_exposure_pct': 0.5, 'no_established_link_pct': 0.25, 'affected_holdings': ['A', 'B', 'C'], 'affected_holdings_count': 3}, attention=ESCALATE
- PASS | 6a. challenges_the_request=True raises MONITOR -> REVIEW | base=MONITOR, challenged=True
- PASS | 6b. challenges_the_request=True does NOT lower ESCALATE | base=ESCALATE, challenged=True -> stays ESCALATE (already above REVIEW)
- PASS | 6c. challenges_the_request=False never changes the base level | unchallenged personas see the same base level as everyone else
- PASS | 7. investigation_status != completed -> zero exposure everywhere, no fabricated loss/exposure | {'what_happened': 'vague unscoped input', 'investigation_status': 'insufficient_evidence', 'attention_level': 'INSUFFICIENT_EVIDENCE', 'no_established_exposure': False, 'direct_exposure_pct': 0.0, 'potential_exposure_pct': 0.0, 'no_established_link_pct': 0.0, 'affected_holdings': [], 'affected_holdings_count': 0, 'why_it_matters': None, 'uncertain': []}
- PASS | 8. Completed briefing: why_it_matters from the real top-tier reason, uncertain flags both signals | why_it_matters='NVDA named directly in the real sanctions filing.' uncertain=['Follow-up question unresolved: "Does the order name AMD?" (unsupported).', 'AMD: only a plausible, unconfirmed connection was found.']
- PASS | 9. no_established_exposure distinguishes true negative from weak-signal MONITOR | all_clear.no_established_exposure=True weak_signal.no_established_exposure=False

14/14 checks passed.
