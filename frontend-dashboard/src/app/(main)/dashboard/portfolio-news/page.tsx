import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { railHeadline } from "@/data/rail-headline";
import { getHoldings } from "@/server/portfolio";

import { HeadlineImpact } from "../stock/[ticker]/_components/headline-impact";
import { StockNews } from "../stock/[ticker]/_components/stock-news";
import { StockNewsLayout } from "../stock/[ticker]/_components/stock-news-layout";
import { NewsFilters } from "./_components/news-filters";

export const metadata: Metadata = { title: "Portfolio News" };

export default async function PortfolioNewsPage({
  searchParams,
}: {
  searchParams: Promise<{ scope?: string; symbol?: string; hours?: string }>;
}) {
  const { scope, symbol, hours } = await searchParams;
  const holdings = await getHoldings();
  const saved = holdings.map((row) => row.ticker);
  const all = scope === "all";
  const ticker = typeof symbol === "string" ? symbol.trim().toUpperCase() : "";
  const equivalent = (s: string) => s.replaceAll(".", "-");
  const symbols = ticker ? [ticker] : all ? undefined : saved;
  const outside = ticker && !all && !saved.some((s) => equivalent(s) === equivalent(ticker));
  const initialCards = (await cookies()).get("stock_news_view")?.value === "cards";
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-3xl tracking-tight">Portfolio News</h1>
      <section id="rail-replay" className="grid justify-items-start gap-2 rounded-xl border bg-card p-4">
        <p className="text-xs text-muted-foreground">Historical replay · August 22, 2024</p>
        <h2 className="text-lg font-medium">{railHeadline.title}</h2>
        <HeadlineImpact demo headline={railHeadline} />
      </section>
      <NewsFilters key={JSON.stringify([all, ticker])} all={all} ticker={ticker} saved={saved} />
      <StockNewsLayout
        heading={
          ticker
            ? `News for ${ticker}${hours === "24" ? " · Past 24 hours" : ""}`
            : all
              ? "Market news"
              : "News for your holdings"
        }
        initialCards={initialCards}
      >
        {outside ? (
          <p className="text-sm text-muted-foreground">
            {ticker} isn’t in your portfolio. Choose All symbols to see its news.
          </p>
        ) : !all && !saved.length ? (
          <p className="text-sm text-muted-foreground">Add a stock to see portfolio news, or choose All symbols.</p>
        ) : (
          <Suspense
            key={JSON.stringify([all, symbols])}
            fallback={<Skeleton className="h-16" aria-label="Loading news" role="status" />}
          >
            <StockNews
              symbols={symbols}
              hours={hours === "24" ? 24 : undefined}
              preferred={ticker ? [ticker] : saved}
            />
          </Suspense>
        )}
      </StockNewsLayout>
    </div>
  );
}
