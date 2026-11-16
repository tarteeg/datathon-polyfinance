import type { Metadata } from "next";

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
  const holdings = await getHoldings();
  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl tracking-tight">News & Geopolitical Intelligence</h1>
        <p className="text-muted-foreground text-sm">
          Simulation only, not investment advice. Real recent articles for your holdings, checked against real
          regulatory sources — never hidden just because nothing was confirmed as a portfolio risk.
        </p>
      </div>
      <PortfolioEventScan key={JSON.stringify(holdings)} hasHoldings={holdings.length > 0} />
      <NewsPageClient />
    </div>
  );
}
