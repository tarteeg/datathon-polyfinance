import type { Metadata } from "next";

import { getHoldings } from "@/server/portfolio";

import { RiskRippleWorkspace } from "./_components/risk-ripple-workspace";

export const metadata: Metadata = {
  title: "Risk Ripple — Trickle-Down Investigation",
  description:
    "Automatically checks real regulatory and news sources against your portfolio for genuine trickle-down risk — not investment advice.",
  alternates: {
    canonical: "/dashboard/risk-ripple",
  },
};

export default async function Page() {
  const holdings = await getHoldings();
  const defaultTickers = holdings.map((holding) => holding.ticker).join(", ");

  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl tracking-tight">Risk Ripple</h1>
        <p className="text-muted-foreground text-sm">
          Simulation only, not investment advice. Checks real regulatory filings and news against your actual
          holdings and surfaces only genuinely evidence-backed connections.
        </p>
      </div>

      <RiskRippleWorkspace defaultTickers={defaultTickers} />
    </div>
  );
}
