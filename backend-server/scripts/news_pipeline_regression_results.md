# News pipeline (direct-mention / three-tier) regression results

Real output from `scripts/test_news_pipeline_regression.py`.

- PASS | 1. Real direct NVIDIA news (no trade vocabulary) produces a match
  - matches=[('NVDA', 'direct')]
- PASS | 2. AMD/NVIDIA competitor mention does not create a bogus supplier edge
  - edges=[]
- PASS | 4. Generic 'semiconductor' overlap vs AAPL still requires Stage-2 verification
  - matches=[('AAPL', True)]
- PASS | 5. Simulated total StocksFeed failure is recorded per-ticker, not silently empty
  - docs=0, diag={'NVDA': {'raw_count': 0, 'error': 'StocksFeedError: simulated outage'}, 'AMD': {'raw_count': 0, 'error': 'StocksFeedError: simulated outage'}}
- PASS | 6. Person-to-company resolution: 'Jensen Huang' alone resolves to NVDA
  - matches=[('NVDA', 'direct')]
