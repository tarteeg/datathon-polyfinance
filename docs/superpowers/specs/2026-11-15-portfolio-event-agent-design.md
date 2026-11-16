# Find recent events that matter to my portfolio

A signed-in user presses **Scan my portfolio** in RiskRipple. The agent reads the user's current holdings, discovers recent events across StocksFeed, and returns the events with the strongest supported connections to the portfolio. Each result answers “Why did this show up for me?” and “Who else could be affected?”

## Trigger and scope

We considered starting from an event the user selects and starting from a portfolio scan. The user chose the scan so discovery happens before they know which story to open. Reuse RiskRipple's background scan and polling pattern. Opening the page displays the last result and its timestamp. Pressing the button starts a scan or joins one already in progress for the same inputs.

Proposed starting defaults are 30 days of published coverage, up to five material events and up to three additional companies per event drawn from the StocksFeed S&P 500 universe. Assess every holding regardless of index membership. A scan can return fewer results, including zero. Show watchlist-only positions separately because they have no position value. For an account with only watchlist entries, rank by supported business relevance and explain that basis.

## Discover the event once

Trading AI already creates versioned catalyst clusters with source article URLs. Extend its eligibility rule to admit a concrete event without ticker tags. Check the article title, substance and event details. Two stories about separate regulatory decisions must remain separate even when both concern the same industry. Keep inferred beneficiaries, suppliers and customers in the analysis. Article ticker tags retain their existing meaning.

Expose recent clusters and their source references through a read-only StocksFeed API. Use publication time of supporting coverage for the lookback and show the event date separately when known. A maintenance edit to an old article alone should never make an event recent. Inspect existing recent unclustered articles, preview affected counts and sample matches, then backfill eligible records. Re-running against the same data must preserve cluster membership and avoid duplicate stories. Record the actual coverage gained.

## Investigate and rank

1. Read portfolio symbols and quantities from the signed-in session. Retrieve recent events across the feed, including events with no company tags.
2. For each plausible event, identify the business change and who might experience it. Use article passages for the event facts. For indirect connections, look up the relevant company filing or another dated primary source for each material link. Existing RiskRipple filing lookup is the starting point. Candidate generation can use industry, product, geography, supplier, customer or substitution relationships.
3. Prioritize events by strength of evidence, significance of the business change and share of the portfolio exposed where current position values are available. Count a holding once even when several paths reach it. Show which holdings drove the rank and the basis for any weights. Use qualitative relevance when values are incomplete. Distinguish missing evidence from a completed search that found no supported link.
4. For each selected event, give every holding a short assessment. For supported links, give the direction of the potential business effect, the mechanism, its main condition and the sources. Allow mixed or uncertain direction. For outside companies, search a bounded shortlist and publish only supported results. Document the search universe with the result.

For example, an article about a hypothetical export restriction could establish which products and destinations it covers. A chip designer's filing could establish sales exposure there. A foundry's filing could establish a customer relationship. The foundry conclusion would still be conditional on the designer reducing orders. If the evidence stops at the designer, the report stops there too.

## Verification

- An untagged, material policy event reaches the scan and outranks routine ticker coverage in a portfolio with a documented business exposure. An unrelated portfolio gets a different ranking or an empty result.
- Two publishers covering the same decision produce one event. Two separate decisions in the same sector produce separate results.
- Every holding has an assessment. An unmentioned outside company can qualify through a sourced relationship. Sharing a sector alone cannot qualify it.
- Source failures show incomplete coverage. An empty successful scan reports the search period. A repeated click joins the current run, and a changed portfolio or revised event cannot reuse a stale assessment.
- Before any backfill, check the database target and eligible record count. Afterward, compare sample articles with their cluster records and repeat the selection to verify the backfill is safe to rerun.
