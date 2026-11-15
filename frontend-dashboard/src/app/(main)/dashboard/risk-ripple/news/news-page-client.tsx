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
    const params = new URLSearchParams({
      event: `${article.title}. ${article.summary}`.trim(),
      tickers: article.ticker ?? "",
    });
    router.push(`/dashboard/risk-ripple/investigations?${params.toString()}`);
  }

  return <NewsWorkspace onInvestigate={handleInvestigateImpact} />;
}
