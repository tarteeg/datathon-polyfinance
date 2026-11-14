import { StockPriceChart } from "../../_components/stock-price-chart";
import type { ChartSnapshot } from "../chart-snapshot";

export function SavedChart({ snapshot }: { snapshot: ChartSnapshot }) {
  const { facts, points } = snapshot;
  const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
  const change = facts.changePercent;
  const date = (seconds: number) => new Date(seconds * 1000).toISOString().replace("T", " ").slice(0, 16);
  return (
    <figure className="my-4 rounded-lg border p-3">
      <figcaption className="font-medium">
        {facts.symbol} · {facts.period} · Yahoo Finance
      </figcaption>
      <p className="text-sm">
        {facts.baselineLabel}: {facts.baseline === null ? "Unavailable" : number.format(facts.baseline)}
        {" · "}Quote: {number.format(facts.quote)} {facts.currency ?? "(currency unavailable)"}
        {change !== null && ` (${change > 0 ? "+" : ""}${number.format(change)}%)`}
      </p>
      <p className="text-xs text-muted-foreground">
        Chart: {date(facts.firstCandle.time)} – {date(facts.lastCandle.time)} UTC. Quote:{" "}
        {facts.quoteTime ? date(facts.quoteTime) + " UTC" : "time unavailable"}.
      </p>
      <StockPriceChart symbol={facts.symbol} points={points} period={facts.period} currency={facts.currency} tone="text-primary" />
    </figure>
  );
}
