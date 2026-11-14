import { redirect } from "next/navigation";
import { requireSession } from "@/lib/session";
import { startChartChat } from "@/server/chart-chat";
import { chartSnapshot } from "../../../chat/chart-snapshot";
import { ExplainChartButton } from "./explain-chart-button";
import { formatCurrency } from "@/lib/utils";
import { fetchHistory } from "@/server/stock-history";
import { StockPriceChart } from "../../../_components/stock-price-chart";
import { PricePanel } from "./price-panel";

export async function StockHistory({ symbol, period }: { symbol: string; period: string }) {
  let history;
  try {
    history = await fetchHistory(symbol, period);
  } catch {
    return (
      <PricePanel symbol={symbol} period={period}>
        <p role="alert">Couldn’t load stock prices. Refresh to try again.</p>
      </PricePanel>
    );
  }
  if (!history)
    return (
      <PricePanel symbol={symbol} period={period}>
        <p>No market data for this period.</p>
      </PricePanel>
    );

  const { ticker, candles } = history;
  const baseline = period === "mtd" ? ticker.priorMonthClose : period === "1d" ? ticker.previousClose : candles[0]?.Close;
  const change = baseline == null ? null : Number((ticker.regularMarketPrice - baseline).toFixed(2));
  const tone =
    change && change > 0
      ? "text-emerald-700 dark:text-emerald-400"
      : change && change < 0
        ? "text-red-700 dark:text-red-400"
        : "text-muted-foreground";
  const quote = ticker.currency
    ? formatCurrency(ticker.regularMarketPrice, { currency: ticker.currency })
    : ticker.regularMarketPrice;
  const asOf = ticker.regularMarketTime != null ? new Date(ticker.regularMarketTime * 1000).toISOString() : undefined;

  const snapshot = candles.length ? chartSnapshot(symbol, period, history) : null;

  async function explain() {
    "use server";
    const { user } = await requireSession();
    if (!snapshot) return "No chart data available.";
    let id: string;
    try {
      id = await startChartChat(user.id, snapshot);
    } catch {
      return "Couldn’t save the chart explanation. Please try again.";
    }
    redirect(`/dashboard/chat?thread=${id}`);
  }

  return (
    <PricePanel
      symbol={symbol}
      period={period}
      name={ticker.name}
      market={[ticker.exchange, ticker.currency].filter(Boolean).join(" · ")}
      price={
        <>
          <span className="text-xl" title={asOf && `Regular market price as of ${asOf}`}>
            {quote}
          </span>
          {change !== null && (
            <span className={tone}>
              {change > 0 ? "+" : ""}
              {change.toFixed(2)}
            </span>
          )}
        </>
      }
    >
      {candles.length ? (
        <StockPriceChart symbol={symbol}
          points={candles.map(({ time, Close }) => ({ time, Close }))}
          period={period}
          currency={ticker.currency}
          tone={tone}
        />
      ) : (
        <p>No trading activity in this period.</p>
      )}
      {snapshot && <ExplainChartButton explain={explain} />}
    </PricePanel>
  );
}
