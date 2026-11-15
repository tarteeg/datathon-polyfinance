"use client";

import { useSearchParams } from "next/navigation";

import { InvestigationsWorkspace } from "../_components/investigations-workspace";

export function InvestigationsPageClient({ defaultTickers }: { defaultTickers: string }) {
  const searchParams = useSearchParams();
  const event = searchParams.get("event");
  const tickers = searchParams.get("tickers");
  const initialPrefill = event ? { eventDescription: event, tickers: tickers ?? "" } : null;

  return <InvestigationsWorkspace defaultTickers={defaultTickers} initialPrefill={initialPrefill} />;
}
