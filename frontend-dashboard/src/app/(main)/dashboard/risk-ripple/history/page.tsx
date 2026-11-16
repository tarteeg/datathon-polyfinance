import type { Metadata } from "next";

import { HistoryWorkspace } from "../_components/history-workspace";

export const metadata: Metadata = {
  title: "Past Investigations",
  description: "Previously completed manual portfolio-risk investigations — not investment advice.",
  alternates: {
    canonical: "/dashboard/risk-ripple/history",
  },
};

export default function Page() {
  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl tracking-tight">Past Investigations</h1>
        <p className="text-muted-foreground text-sm">
          Simulation only, not investment advice. Every manual investigation you've previously run, with its full
          evidence and reasoning — browse or delete past entries here.
        </p>
      </div>
      <HistoryWorkspace />
    </div>
  );
}
