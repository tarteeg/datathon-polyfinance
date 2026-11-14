"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { DialogClose } from "@/components/ui/dialog";

type QuoteChange = { change: number; currency: string | null };

export function RelatedStock({ ticker }: { ticker: string }) {
  const [quote, setQuote] = useState<QuoteChange | null>(null);
  const symbol = encodeURIComponent(ticker);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`/api/stocks/${symbol}/change`, { signal: controller.signal });
        if (response.status === 200) setQuote(await response.json());
      } catch {
        // The ticker remains navigable when market data is unavailable.
      }
    }
    void load();
    return () => controller.abort();
  }, [symbol]);

  const change = quote?.change ?? 0;
  const tone =
    change < 0
      ? "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400"
      : change > 0
        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
        : "";
  const amount =
    quote &&
    new Intl.NumberFormat("en-US", {
      style: quote.currency ? "currency" : "decimal",
      currency: quote.currency ?? undefined,
      signDisplay: "exceptZero",
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(change);

  return (
    <DialogClose asChild>
      <Badge asChild variant="secondary" className={`h-8 px-3 text-sm font-semibold tabular-nums ${tone}`}>
        <Link prefetch={false} href={`/dashboard/stock/${symbol}`} title="Change since the previous close">
          {ticker}
          {amount && ` ${amount}`}
        </Link>
      </Badge>
    </DialogClose>
  );
}
