# Portfolio event scan implementation plan

Implement the approved portfolio event scan in the existing Python services and Next.js dashboard. Use a rolling 30-day window. The design is in ../specs/2026-11-15-portfolio-event-agent-design.md.

1. Extend Trading AI catalyst eligibility and StocksFeed event discovery. Verify tickerless eligibility, publication-date filtering, backfill counts and repeatability.
2. Screen recent event summaries against the signed-in portfolio, then examine publisher and issuer passages for shortlisted events. Verify direct and second-order connections, missing evidence, and outside-catalog filtering.
3. Connect the RiskRipple button to a session-scoped background run, present coverage and evidence, and document the data flow. Check duplicate clicks, watchlists, failed providers and real service responses.
