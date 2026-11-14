import type { Metadata } from "next";

import { getHoldings } from "@/server/portfolio";

import { InvestigateForm } from "./_components/investigate-form";

export const metadata: Metadata = {
  title: "Risk Ripple — Trickle-Down Investigation",
  description:
    "Investigate how a sanctions, export-control, or regulatory event ripples through supplier and material dependencies across your portfolio holdings.",
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
          Simulation only. Investigate trickle-down exposure to a geopolitical, sanctions, or regulatory event across
          your portfolio&apos;s supplier and material dependencies — not investment advice.
        </p>
      </div>
      <InvestigateForm defaultTickers={defaultTickers} />
    </div>
  );
}
