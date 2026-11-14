import "server-only";
import { cache } from "react";

export type StockHistoryData = {
  ticker: {
    previousClose?: number | null;
    name: string;
    exchange?: string | null;
    regularMarketPrice: number;
    currency: string | null;
    regularMarketTime: number | null;
  };
  candles: { time: number; Close: number }[];
};

export const fetchHistory = cache(async (symbol: string, period: string): Promise<StockHistoryData | null> => {
  const backend = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  // Yahoo uses hyphens for share classes, e.g. BRK.B is BRK-B.
  const ticker = encodeURIComponent(symbol.replaceAll(".", "-"));
  const response = await fetch(new URL(`/stock/${ticker}/history?period=${period}`, backend), {
    cache: "no-store",
    signal: AbortSignal.timeout(30000),
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Stock history unavailable");
  return (await response.json()).history;
});
