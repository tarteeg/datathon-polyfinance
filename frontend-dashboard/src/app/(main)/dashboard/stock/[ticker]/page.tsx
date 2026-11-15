import { cookies } from "next/headers";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { StockHistory } from "./_components/stock-history";
import { StockHistorySkeleton } from "./_components/stock-history-skeleton";
import { StockNews } from "./_components/stock-news";
import { StockNewsLayout } from "./_components/stock-news-layout";

import { periodLabels } from "./_components/price-panel";

export default async function StockPage({
  params,
  searchParams,
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ period?: string | string[]; source?: string | string[] }>;
}) {
  const symbol = (await params).ticker.toUpperCase();
  const initialCards = (await cookies()).get("stock_news_view")?.value === "cards";
  const { period: requested, source: requestedSource } = await searchParams;
  const source = typeof requestedSource === "string" ? requestedSource : "";
  const period = typeof requested === "string" && Object.hasOwn(periodLabels, requested) ? requested : "5d";

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-7">
      <Suspense key={`${symbol}-${period}`} fallback={<StockHistorySkeleton symbol={symbol} period={period} source={source} />}>
        <StockHistory symbol={symbol} period={period} source={source} />
      </Suspense>
      <StockNewsLayout heading={`News for ${symbol}`} initialCards={initialCards}>
        <Suspense key={symbol} fallback={<Skeleton className="h-16" role="status" aria-label="Loading stock news" />}>
          <StockNews source={source} symbols={[symbol]} />
        </Suspense>
      </StockNewsLayout>
    </div>
  );
}
