import type { Metadata } from "next";
import { Suspense } from "react";

import { getHoldings } from "@/server/portfolio";

import { InvestigationsPageClient } from "./investigations-page-client";

export const metadata: Metadata = {
  title: "Portfolio Risk & Investigations",
  description:
    "Confirmed exposure alerts, open candidates, and past investigations for your real portfolio — not investment advice.",
  alternates: {
    canonical: "/dashboard/risk-ripple/investigations",
  },
};

export default async function Page() {
  const holdings = await getHoldings();
  const defaultTickers = holdings.map((holding) => holding.ticker).join(", ");

  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl tracking-tight">Portfolio Risk & Investigations</h1>
        <p className="text-muted-foreground text-sm">
          Simulation only, not investment advice. Checks real regulatory filings and news against your actual
          holdings and surfaces only genuinely evidence-backed connections. Works even when nothing is confirmed.
        </p>
      </div>
      <Suspense fallback={null}>
        <InvestigationsPageClient defaultTickers={defaultTickers} />
      </Suspense>
    </div>
  );
}
