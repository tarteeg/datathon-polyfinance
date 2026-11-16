"use client";

import { useRouter } from "next/navigation";

import { NewsWorkspace } from "../_components/news-workspace";
import type { NewsArticle } from "@/server/riskripple";

// "Investigate Impact" on this page hands off to the Investigations page (where the
// manual investigate form now lives) via query params, rather than duplicating the
// investigation mechanism here.
export function NewsPageClient() {
  const router = useRouter();

  function handleInvestigateImpact(article: NewsArticle) {
    // Deliberately no `tickers` param -- the percentages on the resulting briefing
    // are "% of portfolio weight in each evidence tier," which is only meaningful
    // against the real full portfolio. Narrowing to just this one article's ticker
    // made every single-article investigation degenerate to 0%/100%/0% (confirmed:
    // with exactly one ticker checked, the distribution can only ever be binary).
    // Falls through to the form's real-portfolio default (see investigate-form.tsx).
    const params = new URLSearchParams({
      event: `${article.title}. ${article.summary}`.trim(),
    });
    router.push(`/dashboard/risk-ripple/investigations?${params.toString()}`);
  }

  return <NewsWorkspace onInvestigate={handleInvestigateImpact} />;
}
