import { cookies } from "next/headers";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { getHoldings } from "@/server/portfolio";

import { AddStockDialog } from "../_components/sidebar/add-stock-dialog";
import { StockNews } from "../stock/[ticker]/_components/stock-news";
import { StockNewsLayout } from "../stock/[ticker]/_components/stock-news-layout";
import { NewsFilters } from "./_components/news-filters";
import { Discover } from "./_components/discover";
import { HomeTabs } from "./_components/home-tabs";
import { Portfolio } from "./_components/portfolio";

type Filters = { tab?: string; scope?: string; symbol?: string; sector?: string; hours?: string };

async function HomeNews({ scope, symbol, hours }: Filters) {
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
      <NewsFilters key={JSON.stringify([all, ticker])} all={all} ticker={ticker} saved={saved} />
      <StockNewsLayout
        heading={
          ticker
            ? `News for ${ticker}${hours === "24" ? " · Past 24 hours" : ""}`
            : all
              ? "Market news"
              : "Portfolio news"
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

export default async function HomePage({ searchParams }: { searchParams: Promise<Filters> }) {
  const filters = await searchParams;
  const tab = filters.tab === "news" ? "news" : "portfolio";
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-3xl tracking-tight">Portfolio and market activity</h1>
      <HomeTabs tab={tab}>
        {tab === "news" ? (
          <HomeNews {...filters} />
        ) : (
          <div className="flex flex-col items-stretch gap-4">
            <div>
              <AddStockDialog sidebar={false} />
            </div>
            <Suspense fallback={<Skeleton className="h-32" role="status" aria-label="Loading portfolio" />}>
              <Portfolio />
            </Suspense>
            <div className="mt-6 min-w-0 border-t pt-7">
              <Suspense fallback={<Skeleton className="h-64" role="status" aria-label="Loading rankings" />}>
                <Discover sector={filters.sector} />
              </Suspense>
            </div>
          </div>
        )}
      </HomeTabs>
    </div>
  );
}
