import Link from "next/link";
import { Suspense } from "react";

import { SectorFilter } from "./sector-filter";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getHoldings } from "@/server/portfolio";
import { fetchHistory } from "@/server/stock-history";
import { AddStockDialog } from "../../_components/sidebar/add-stock-dialog";

type Stock = { ticker: string; name: string; sector: string; article_count: number };
type Ranking = { sectors: string[]; stocks: Stock[]; as_of: string };

async function DailyPerformance({ ticker }: { ticker: string }) {
  const history = await fetchHistory(ticker, "1d").catch(() => null);
  if (!history) return <>—</>;

  const { regularMarketPrice: price, currency, previousClose } = history.ticker;
  const money: Intl.NumberFormatOptions = {
    ...(currency ? ({ style: "currency", currency, currencyDisplay: "narrowSymbol" } as const) : {}),
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  };
  const change = previousClose != null && previousClose > 0 ? price - previousClose : null;

  return (
    <div className="flex flex-col gap-0.5 tabular-nums">
      <strong>
        {price.toLocaleString("en-US", money)} {currency}
      </strong>
      {change !== null && previousClose ? (
        <span
          className={
            change > 0
              ? "text-emerald-700 dark:text-emerald-400"
              : change < 0
                ? "text-red-700 dark:text-red-400"
                : "text-muted-foreground"
          }
        >
          {change.toLocaleString("en-US", { ...money, signDisplay: "exceptZero" })}{" "}
          {(change / previousClose).toLocaleString("en-US", {
            style: "percent",
            signDisplay: "exceptZero",
            minimumFractionDigits: 2,
          })}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      )}
    </div>
  );
}

export async function Discover({ sector }: { sector?: string }) {
  const url = new URL("/stocks/most-mentioned", process.env.BACKEND_API_URL || "http://127.0.0.1:8000");
  if (sector) url.searchParams.set("sector", sector);
  let ranking: Ranking;
  try {
    const response = await fetch(url, { next: { revalidate: 60 }, signal: AbortSignal.timeout(25000) });
    if (!response.ok) throw new Error("Ranking unavailable");
    ranking = await response.json();
  } catch {
    return (
      <p role="alert">
        Couldn’t load the ranking.{" "}
        <Link className="underline" href="/dashboard/home">
          View all sectors
        </Link>
      </p>
    );
  }
  const saved = new Set((await getHoldings()).map((row) => row.ticker));
  return (
    <section className="min-w-0 overflow-hidden rounded-xl border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold tracking-tight">Most-mentioned stocks</h2>
          <p className="text-sm text-muted-foreground">
            S&amp;P 500 stocks ranked by distinct news articles in the last 24 hours.
          </p>
        </div>
        <SectorFilter sector={sector} sectors={ranking.sectors} />
      </div>
      {ranking.stocks.length ? (
        <Table aria-label="Most-mentioned stocks">
          <TableHeader className="bg-muted/20 text-xs">
            <TableRow>
              <TableHead className="hidden w-14 pl-6 sm:table-cell">#</TableHead>
              <TableHead className="pl-4 sm:pl-2">Company</TableHead>
              <TableHead className="hidden text-right sm:table-cell">Articles</TableHead>
              <TableHead className="text-right">Daily performance</TableHead>
              <TableHead className="text-right">
                <span className="sr-only">Portfolio</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ranking.stocks.map((s, i) => (
              <TableRow key={s.ticker}>
                <TableCell className="hidden pl-6 text-muted-foreground tabular-nums sm:table-cell">{i + 1}</TableCell>
                <TableCell className="pl-4 sm:pl-2">
                  <Link
                    className="block py-1.5 hover:underline"
                    href={`/dashboard/stock/${encodeURIComponent(s.ticker)}`}
                    prefetch={false}
                  >
                    <strong>{s.ticker}</strong>
                    <span className="block max-w-24 truncate text-xs text-muted-foreground sm:max-w-64">{s.name}</span>
                    <span className="block text-xs text-muted-foreground sm:hidden">
                      {s.article_count} {s.article_count === 1 ? "article" : "articles"}
                    </span>
                  </Link>
                </TableCell>
                <TableCell className="hidden text-right tabular-nums sm:table-cell">{s.article_count}</TableCell>
                <TableCell className="text-right">
                  <Suspense fallback="…">
                    <DailyPerformance ticker={s.ticker} />
                  </Suspense>
                </TableCell>
                <TableCell className="pr-4 text-right sm:pr-6">
                  {saved.has(s.ticker) ? (
                    <span title="In portfolio" className="text-muted-foreground">
                      ✓<span className="sr-only sm:not-sr-only"> In portfolio</span>
                    </span>
                  ) : (
                    <AddStockDialog sidebar={false} initialTicker={s.ticker} />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="p-5 text-sm text-muted-foreground">No mentions in this sector in the past 24 hours.</p>
      )}
    </section>
  );
}
