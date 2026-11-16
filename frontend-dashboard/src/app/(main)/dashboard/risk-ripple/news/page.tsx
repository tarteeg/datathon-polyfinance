import type { Metadata } from "next";

import { requireSession } from "@/lib/session";
import { getHoldings } from "@/server/portfolio";
import { PortfolioEventScan } from "../_components/portfolio-event-scan";
import { NewsPageClient } from "./news-page-client";

export const metadata: Metadata = {
  title: "News & Geopolitical Intelligence",
  description:
    "Real recent news for your portfolio holdings and the broader geopolitical/regulatory landscape — not investment advice.",
  alternates: {
    canonical: "/dashboard/risk-ripple/news",
  },
};

export default async function Page() {
  const [holdings, { user }] = await Promise.all([getHoldings(), requireSession()]);
  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-balance text-3xl font-semibold tracking-tight">News & Geopolitical Intelligence</h1>
        <p className="text-muted-foreground text-sm">
          Explore portfolio news and regulatory evidence. For simulation only, not investment advice.
        </p>
      </div>
      <PortfolioEventScan key={JSON.stringify([holdings, user.investorPersona])} positionCount={holdings.length} />
      <NewsPageClient key={JSON.stringify([user.investorPersona, holdings])} />
    </div>
  );
}
