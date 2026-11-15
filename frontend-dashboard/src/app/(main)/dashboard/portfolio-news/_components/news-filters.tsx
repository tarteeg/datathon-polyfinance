"use client";

import { BriefcaseBusiness, Globe2, LoaderCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { StockPicker } from "../../_components/stock-picker";

export function NewsFilters({ all, ticker, saved }: { all: boolean; ticker: string; saved: string[] }) {
  const router = useRouter();
  const search = useSearchParams();
  const [pending, startTransition] = useTransition();

  function navigate(market: boolean, symbol: string) {
    const params = new URLSearchParams(search.toString());
    if (market) params.set("scope", "all");
    else params.delete("scope");
    if (symbol) params.set("symbol", symbol);
    else params.delete("symbol");
    const query = params.toString();
    startTransition(() => router.push(`/dashboard/portfolio-news${query ? "?" + query : ""}`, { scroll: false }));
  }

  return (
    <div aria-busy={pending} className="contents sm:flex sm:min-w-0 sm:flex-wrap sm:items-center sm:gap-2">
      <ToggleGroup
        type="single"
        variant="outline"
        spacing={0}
        className="col-span-2"
        aria-label="News scope"
        value={all ? "all" : "portfolio"}
        disabled={pending}
        onValueChange={(scope) => {
          if (!scope) return;
          const market = scope === "all";
          const inPortfolio = saved.some((symbol) => symbol.replaceAll(".", "-") === ticker.replaceAll(".", "-"));
          navigate(market, market || inPortfolio ? ticker : "");
        }}
      >
        <ToggleGroupItem value="portfolio"><BriefcaseBusiness />My portfolio</ToggleGroupItem>
        <ToggleGroupItem value="all"><Globe2 />All symbols</ToggleGroupItem>
      </ToggleGroup>
      <div className="flex min-w-0 items-center gap-2 sm:w-56">
        <StockPicker filter ticker={ticker} symbols={all ? undefined : saved} onSelect={(symbol) => navigate(all, symbol)} disabled={pending} />
        {pending && <span role="status"><LoaderCircle aria-hidden className="size-4 animate-spin" /><span className="sr-only">Updating news</span></span>}
      </div>
    </div>
  );
}
