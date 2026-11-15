import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { sp500 } from "@/data/sp500";
import { formatCurrency } from "@/lib/utils";
import { getHoldings } from "@/server/portfolio";
import { fetchHistory } from "@/server/stock-history";
import { Sparkline } from "../../_components/sidebar/portfolio-price";

import { EditShares } from "./edit-shares";

export async function Portfolio() {
  const holdings = await getHoldings();
  if (!holdings.length)
    return (
      <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
        Add a stock to start your portfolio.
      </p>
    );
  const rows = await Promise.all(
    holdings.map(async (holding) => {
      const history = await fetchHistory(holding.ticker, "1d").catch(() => null);
      const price = history?.ticker.regularMarketPrice;
      const previous = history?.ticker.previousClose;
      const change = price != null && previous != null ? price - previous : null;
      const value = price != null && holding.quantity != null ? price * Number(holding.quantity) : null;
      return { ...holding, history, price, previous, change, value, currency: history?.ticker.currency };
    }),
  );
  const totals = new Map<string, number>();
  for (const row of rows) {
    if (row.value != null && row.currency) totals.set(row.currency, (totals.get(row.currency) ?? 0) + row.value);
  }
  const positions = rows.filter((row) => row.quantity != null);
  const watchlist = rows.length - positions.length;
  const complete = positions.length > 0 && positions.every((row) => row.value != null && row.currency);
  const daily = new Map<string, number>();
  for (const row of positions) {
    if (row.change != null && row.currency) {
      daily.set(row.currency, (daily.get(row.currency) ?? 0) + row.change * Number(row.quantity));
    }
  }
  const dailyComplete = complete && positions.every((row) => row.change != null);
  return (
    <section aria-label="Your portfolio" className="min-w-0 overflow-hidden rounded-xl border bg-card">
      <dl className="grid grid-cols-2 gap-4 border-b bg-muted/25 px-4 py-5 sm:grid-cols-[2fr_1.5fr_1fr] sm:px-6">
        <div className="col-span-2 sm:col-span-1">
          <dt className="text-sm text-muted-foreground">Holdings value</dt>
          <dd className="mt-1 text-3xl font-semibold tracking-tight tabular-nums">
            {complete
              ? [...totals]
                  .map(
                    ([currency, value]) =>
                      formatCurrency(value, { currency }) + (totals.size > 1 ? ` ${currency}` : ""),
                  )
                  .join(" + ")
              : positions.length
                ? "Unavailable"
                : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Day change</dt>
          <dd className="mt-1 flex flex-wrap gap-x-2 text-xl font-semibold tracking-tight tabular-nums">
            {dailyComplete
              ? [...daily].map(([currency, value]) => (
                  <span
                    key={currency}
                    className={
                      value > 0
                        ? "text-emerald-700 dark:text-emerald-400"
                        : value < 0
                          ? "text-red-700 dark:text-red-400"
                          : undefined
                    }
                  >
                    {value > 0 ? "+" : ""}
                    {formatCurrency(value, { currency })}
                    {daily.size > 1 && ` ${currency}`}
                  </span>
                ))
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Positions</dt>
          <dd className="mt-1 flex flex-wrap items-baseline gap-x-2">
            <span className="text-xl font-semibold tabular-nums">{positions.length}</span>
            {watchlist > 0 && <span className="text-xs text-muted-foreground">{watchlist} on watchlist</span>}
          </dd>
        </div>
      </dl>
      <Table aria-label="Portfolio holdings">
        <TableHeader className="bg-muted/20 text-xs">
          <TableRow>
            <TableHead className="pl-4 sm:pl-6">Stock</TableHead>
            <TableHead className="text-right">Last price</TableHead>
            <TableHead className="pr-4 text-right sm:pr-2">Day change</TableHead>
            <TableHead className="hidden text-center lg:table-cell">Intraday</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Shares</TableHead>
            <TableHead className="hidden pr-6 text-right sm:table-cell">Market value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(({ ticker, quantity, history, price, previous, change, value, currency }) => {
            const money = (n: number) => (currency ? formatCurrency(n, { currency }) : n.toFixed(2));
            const tone = !change
              ? "text-muted-foreground"
              : change > 0
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-red-700 dark:text-red-400";
            return (
              <TableRow key={ticker}>
                <TableCell className="py-3 pl-4 sm:pl-6">
                  <div className="flex items-center gap-1">
                    <Link
                      href={`/dashboard/stock/${encodeURIComponent(ticker)}`}
                      prefetch={false}
                      className="block hover:underline"
                    >
                      <span className="font-semibold">{ticker}</span>
                      <span className="block max-w-24 truncate text-xs text-muted-foreground sm:max-w-60">
                        {sp500[ticker] ?? history?.ticker.name}
                      </span>
                      <span className="block text-xs text-muted-foreground sm:hidden">
                        {value != null ? money(value) + " held" : quantity == null ? "Watchlist" : null}
                      </span>
                    </Link>
                    <EditShares ticker={ticker} quantity={quantity} mobile />
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{price != null ? money(price) : "—"}</TableCell>
                <TableCell className={`pr-4 text-right tabular-nums sm:pr-2 ${tone}`}>
                  {change != null ? (change > 0 ? "+" : "") + money(change) : "—"}
                  {change != null && !!previous && (
                    <span className="block text-xs">
                      {change > 0 ? "+" : ""}
                      {((change / previous) * 100).toFixed(2)}%
                    </span>
                  )}
                </TableCell>
                <TableCell className={`hidden lg:table-cell ${tone}`}>
                  {history?.candles.length ? (
                    <div className="flex justify-center">
                      <Sparkline closes={history.candles.map((c) => c.Close)} baseline={previous ?? null} />
                    </div>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell className="hidden text-right tabular-nums sm:table-cell">
                  <EditShares ticker={ticker} quantity={quantity} />
                </TableCell>
                <TableCell className="hidden pr-6 text-right font-medium tabular-nums sm:table-cell">
                  {value != null ? money(value) : "—"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </section>
  );
}
