import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { getHoldings } from "@/server/portfolio";

import { StockNews } from "../stock/[ticker]/_components/stock-news";
import { StockNewsLayout } from "../stock/[ticker]/_components/stock-news-layout";
import { NewsFilters } from "./_components/news-filters";

export const metadata: Metadata = { title: "Portfolio News" };

export default async function PortfolioNewsPage({
  searchParams,
}: {
  searchParams: Promise<{ scope?: string; symbol?: string; hours?: string; source?: string }>;
}) {
  const { scope, symbol, hours, source } = await searchParams;
  const holdings = await getHoldings();
  const saved = holdings.map((row) => row.ticker);
  const all = scope === "all";
  const ticker = typeof symbol === "string" ? symbol.trim().toUpperCase() : "";
  const equivalent = (s: string) => s.replaceAll(".", "-");
  const symbols = ticker ? [ticker] : all ? undefined : saved;
  const outside = ticker && !all && !saved.some((s) => equivalent(s) === equivalent(ticker));
  const initialCards = (await cookies()).get("stock_news_view")?.value !== "rows";
  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-5">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Portfolio News</h1>
      <StockNewsLayout
        heading={
          ticker
            ? `News for ${ticker}${hours === "24" ? " · Past 24 hours" : ""}`
            : all
              ? "Market news"
              : "News for your holdings"
        }
        filters={<NewsFilters all={all} ticker={ticker} saved={saved} />}
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
            fallback={<Skeleton className="h-36" aria-label="Loading news" role="status" />}
          >
            <StockNews
              source={typeof source === "string" ? source : ""}
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
