# Discovery + risk-metrics regression results

Real output from `scripts/test_discovery_and_risk_metrics_regression.py`.

- **PASS** | 1. discovered_entity/ticker populated when the real trace named one | `followup={'question': 'Does GLOBALFOUNDRIES have Canadian operations?', 'tool_used': 'search_sec_edgar_live', 'classification': 'unresolved', 'summary': "No hits found; GLOBALFOUNDRIES is private, doesn't file 10-Ks.", 'discovered_entity': 'GLOBALFOUNDRIES', 'discovered_ticker': 'GFS', 'discovery_relevance': 'Named AMD wafer supplier with US fabs; Canada exposure unconfirmed.'}`
- **PASS** | 2. discovered_entity absent/None when nothing new was found (not forced) | `followup={'question': "Does NVDA's 10-K name Microsoft as a revenue-concentration customer?", 'tool_used': 'search_sec_edgar_live', 'classification': 'unresolved', 'summary': 'No hits found naming Microsoft specifically.'}`
- **PASS** | 3. Correlation degrades to an explicit message (not a crash/omission) for 1 holding | `correlation='Correlation requires at least 2 holdings with sufficient real price history; only 1 of 1 qualified.'`
- **PASS** | 3b. Drawdown still computes for the single real holding that does have history | `drawdown={'NVDA': {'max_drawdown_pct': -0.3688683518628122, 'peak_date': '2025-01-06', 'trough_date': '2025-04-04', 'recovery_date': '2025-06-25'}}`
- **PASS** | 4. Drawdown degrades to an explicit message for a ticker with no real price history | `drawdown={'ZZZZNOTAREALTICKER': 'Not enough real price history to compute a drawdown estimate.'}`
- **PASS** | 5. Correlation computes a real matrix for 2 real holdings with sufficient history | `correlation={'NVDA': {'NVDA': 1.0, 'AMD': 0.5262217357679806}, 'AMD': {'NVDA': 0.5262217357679806, 'AMD': 1.0}}`
