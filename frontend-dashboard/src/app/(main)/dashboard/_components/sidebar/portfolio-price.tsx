import { formatCurrency } from "@/lib/utils";
import { fetchHistory } from "@/server/stock-history";

export function Sparkline({ closes, baseline }: { closes: number[]; baseline: number | null }) {
  if (closes.length < 2) return null;
  const low = Math.min(...closes, baseline ?? closes[0]);
  const high = Math.max(...closes, baseline ?? closes[0]);
  const y = (price: number) => (high === low ? 16 : 30 - ((price - low) / (high - low)) * 28);
  const points = closes
    .map((price, i) => `${((i * 80) / (closes.length - 1)).toFixed(1)},${y(price).toFixed(1)}`)
    .join(" ");

  return (
    <svg aria-hidden="true" viewBox="0 0 80 32" className="h-8! w-20! shrink-0">
      {baseline !== null && (
        <line
          x1="0"
          x2="80"
          y1={y(baseline)}
          y2={y(baseline)}
          stroke="currentColor"
          strokeDasharray="2 2"
          opacity=".55"
        />
      )}
      <polygon points={`0,32 ${points} 80,32`} fill="currentColor" opacity=".1" />
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export async function PortfolioPrice({ ticker }: { ticker: string }) {
  const history = await fetchHistory(ticker, "1d").catch(() => null);
  if (!history) return <span aria-label="Price unavailable">—</span>;

  const { previousClose, regularMarketPrice, currency } = history.ticker;
  const change = previousClose == null ? null : Number((regularMarketPrice - previousClose).toFixed(2));
  const tone =
    change === null || change === 0
      ? "text-muted-foreground"
      : change > 0
        ? "text-emerald-700 dark:text-emerald-400"
        : "text-red-700 dark:text-red-400";
  const signed = change === null ? "—" : `${change > 0 ? "+" : ""}${change.toFixed(2)}`;

  return (
    <>
      <span className={tone}>
        <Sparkline closes={history.candles.map((candle) => candle.Close)} baseline={previousClose ?? null} />
      </span>
      <span className="flex flex-col items-end gap-0.5 tabular-nums">
        <span className="text-sm font-semibold">
          {currency ? formatCurrency(regularMarketPrice, { currency }) : regularMarketPrice}
        </span>
        <span
          className={`rounded px-1.5 text-xs font-medium ${tone} bg-current/10`}
          aria-label={change === null ? "Daily change unavailable" : `Daily change ${signed}`}
        >
          {signed}
        </span>
      </span>
    </>
  );
}
