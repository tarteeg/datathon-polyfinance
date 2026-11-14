import type { StockHistoryData } from "@/server/stock-history";

export function chartSnapshot(symbol: string, period: string, history: StockHistoryData) {
  const { ticker, candles } = history;
  const points = candles.map(({ time, Close }) => ({ time, Close }));
  const first = points[0];
  const last = points[points.length - 1];
  const baseline = period === "1d" ? (ticker.previousClose ?? null) : first.Close;
  let biggestMove: { from: number; to: number; percent: number } | null = null;
  for (let i = 1; i < points.length; i++) {
    const before = points[i - 1];
    if (!before.Close) continue;
    const percent = (points[i].Close / before.Close - 1) * 100;
    if (!biggestMove || Math.abs(percent) > Math.abs(biggestMove.percent)) {
      biggestMove = { from: before.time, to: points[i].time, percent };
    }
  }
  return {
    points,
    facts: {
      source: "Yahoo Finance",
      symbol,
      name: ticker.name,
      period,
      currency: ticker.currency,
      firstCandle: first,
      lastCandle: last,
      quote: ticker.regularMarketPrice,
      quoteTime: ticker.regularMarketTime,
      baseline,
      baselineLabel: period === "1d" ? "Previous close" : "First chart close",
      changePercent: baseline ? (ticker.regularMarketPrice / baseline - 1) * 100 : null,
      biggestMove,
    },
  };
}

export type ChartSnapshot = ReturnType<typeof chartSnapshot>;
