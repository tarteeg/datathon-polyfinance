import { redirect } from "next/navigation";
import { requireSession } from "@/lib/session";
import { startChartChat } from "@/server/chart-chat";
import { chartSnapshot } from "../../../chat/chart-snapshot";
import { ExplainChartButton } from "./explain-chart-button";
import { formatCurrency } from "@/lib/utils";
import { fetchHistory } from "@/server/stock-history";
import { StockPriceChart } from "../../../_components/stock-price-chart";
import { periodLabels, PricePanel } from "./price-panel";

export async function StockHistory({ symbol, period, source }: { symbol: string; period: string; source: string }) {
  let history;
  try {
    history = await fetchHistory(symbol, period);
  } catch {
    return (
      <PricePanel symbol={symbol} period={period} source={source}>
        <p role="alert">Couldn’t load stock prices. Refresh to try again.</p>
      </PricePanel>
    );
  }
  if (!history)
    return (
      <PricePanel symbol={symbol} period={period} source={source}>
        <p>No market data for this period.</p>
      </PricePanel>
    );

  const { ticker, candles } = history;
  const snapshot = candles.length ? chartSnapshot(symbol, period, history) : null;
  const baseline =
    snapshot?.facts.baseline ??
    (period === "1d" ? ticker.previousClose : period === "mtd" ? ticker.priorMonthClose : null);
  const change = baseline == null ? null : ticker.regularMarketPrice - baseline;
  const percent = baseline && change !== null ? (change / baseline) * 100 : null;
  const tone =
    change === null || change === 0
      ? "text-muted-foreground"
      : change > 0
        ? "text-emerald-700 dark:text-emerald-400"
        : "text-red-700 dark:text-red-400";
  const money = (value: number) =>
    ticker.currency ? formatCurrency(value, { currency: ticker.currency }) : value.toFixed(2);
  const asOf = ticker.regularMarketTime != null ? new Date(ticker.regularMarketTime * 1000) : null;
  const closes = candles.map(({ Close }) => Close);

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
      source={source}
      symbol={symbol}
      period={period}
      name={ticker.name}
      market={[ticker.exchange, ticker.currency].filter(Boolean).join(" · ")}
      action={snapshot && <ExplainChartButton explain={explain} />}
      price={
        <>
          <span className="text-3xl font-semibold tracking-tight sm:text-4xl">{money(ticker.regularMarketPrice)}</span>
          {change !== null && (
            <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <span className={`font-semibold ${tone}`}>
                {change > 0 ? "+" : ""}
                {change.toFixed(2)}
                {percent !== null && ` (${percent > 0 ? "+" : ""}${percent.toFixed(2)}%)`}
              </span>
              <span className="text-muted-foreground">{periodLabels[period]}</span>
            </div>
          )}
        </>
      }
    >
      {snapshot ? (
        <StockPriceChart
          symbol={symbol}
          points={snapshot.points}
          period={period}
          currency={ticker.currency}
          tone={tone}
        />
      ) : (
        <p>No trading activity in this period.</p>
      )}
      <div className="mt-3 flex flex-wrap items-end justify-between gap-3 border-t pt-4">
        {closes.length > 0 && (
          <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            {(
              [
                ["Lowest close", Math.min(...closes)],
                ["Highest close", Math.max(...closes)],
              ] as const
            ).map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-muted-foreground">{label}</dt>
                <dd className="mt-0.5 font-medium tabular-nums">{money(value)}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="text-xs text-muted-foreground">
          Yahoo Finance
          {asOf && (
            <>
              {" "}
              · Quote as of{" "}
              <time dateTime={asOf.toISOString()}>
                {asOf.toLocaleString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                  timeZone: "America/New_York",
                  timeZoneName: "short",
                })}
              </time>
            </>
          )}
        </p>
      </div>
    </PricePanel>
  );
}
