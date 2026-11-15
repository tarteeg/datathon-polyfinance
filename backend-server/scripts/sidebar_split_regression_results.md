# Sidebar split regression results

- **PASS** 1a. Recent-but-old-schema cache row is treated as stale — schema_version=0 vs current=1
- **PASS** 1b. Recent, current-schema cache row is still treated as fresh (caching not disabled) — schema_version=1 matches current
- **PASS** 1c. Missing cache (None) is never fresh — no cache row at all
- **PASS** 2. Empty confirmed_alerts does not imply or require empty articles/candidates — articles=2, candidates=1, confirmed=0
- **PASS** 3. Empty news scan shape's declared lists are all actually empty (no phantom counts) — {'articles': 0, 'investigation_candidates': 0, 'confirmed_alerts': 0}
