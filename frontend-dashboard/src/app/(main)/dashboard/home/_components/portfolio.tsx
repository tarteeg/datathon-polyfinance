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
  if (!holdings.length) return <p className="text-sm text-muted-foreground">Add a stock to start your portfolio.</p>;
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
  const incomplete = rows.some((row) => row.quantity != null && (row.value == null || !row.currency));
  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="text-sm text-muted-foreground">Value of recorded holdings</div>
        <div className="text-2xl font-semibold tabular-nums">
          {incomplete
            ? "Unavailable"
            : [...totals].map(([currency, value]) => formatCurrency(value, { currency })).join(" + ") || "—"}
        </div>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Stock</TableHead>
            <TableHead className="text-right">Last price</TableHead>
            <TableHead className="text-right">Day change</TableHead>
            <TableHead className="hidden lg:table-cell">Intraday</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Shares</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Market value</TableHead>
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
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Link
                      href={`/dashboard/stock/${encodeURIComponent(ticker)}`}
                      prefetch={false}
                      className="block hover:underline"
                    >
                      <span className="font-semibold">{ticker}</span>
                      <span className="block max-w-32 truncate text-xs text-muted-foreground sm:max-w-60">
                        {sp500[ticker] ?? history?.ticker.name}
                      </span>
                    </Link>
                    <EditShares ticker={ticker} quantity={quantity} mobile />
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{price != null ? money(price) : "—"}</TableCell>
                <TableCell className={`text-right tabular-nums ${tone}`}>
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
                    <Sparkline closes={history.candles.map((c) => c.Close)} baseline={previous ?? null} />
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell className="hidden text-right tabular-nums sm:table-cell">
                  <EditShares ticker={ticker} quantity={quantity} />
                </TableCell>
                <TableCell className="hidden text-right tabular-nums sm:table-cell">
                  {value != null ? money(value) : "—"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
