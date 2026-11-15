import { Area, AreaChart, CartesianGrid, ReferenceDot, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

import { money, percent, type Replay, statusLabel } from "./types";

export function HistoricalReplay({ replay }: { replay: Replay }) {
  const trough = replay.series.find((point) => point.date === replay.trough);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Historical stress replay</CardTitle>
        <CardDescription>Simulated portfolio value using observed adjusted closes · USD</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            ["Cumulative return", replay.total_return_pct],
            ["Annualized volatility", replay.volatility_pct],
            ["Maximum drawdown", replay.max_drawdown_pct],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="text-2xl font-semibold tabular-nums">{percent(Number(value))}</dd>
            </div>
          ))}
        </dl>
        <ChartContainer config={{ usd: { label: "Portfolio value", color: "var(--chart-1)" } }} className="h-60 w-full">
          <AreaChart data={replay.series} accessibilityLayer margin={{ left: 2, right: 12, top: 6 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickLine={false} axisLine={false} minTickGap={42} />
            <YAxis domain={["auto", "auto"]} tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`} width={57} />
            <ChartTooltip content={<ChartTooltipContent formatter={(v) => money(Number(v))} />} />
            <Area
              dataKey="usd"
              type="linear"
              stroke="var(--color-usd)"
              strokeWidth={2}
              fill="var(--color-usd)"
              fillOpacity={0.12}
              isAnimationActive={false}
            />
            {trough && replay.max_drawdown_pct < 0 && (
              <ReferenceDot x={trough.date} y={trough.usd} r={4} fill="var(--foreground)" stroke="var(--background)" />
            )}
          </AreaChart>
        </ChartContainer>
        <p>
          <strong>{statusLabel[replay.drawdown_status]}.</strong> The largest peak-to-trough loss was{" "}
          {percent(Math.abs(replay.max_drawdown_pct))}, from {replay.peak} to {replay.trough}.
        </p>
        <details className="rounded-lg border p-3">
          <summary className="cursor-pointer font-medium">Evidence, contributions and assumptions</summary>
          <div className="text-muted-foreground mt-3 flex flex-col gap-2 text-sm">
            <p>
              {replay.trading_days} aligned US trading sessions. Baseline close {replay.baseline}, final close{" "}
              {replay.last_close}. Each session must have an adjusted price for both funds.
            </p>
            <p>
              Weights reset every trading day. Adjusted closes include splits and distributions. Volatility uses sample
              daily returns and 252 sessions per year. Trading costs, fees for rebalancing and taxes are excluded.
            </p>
            <p>
              Contributions to cumulative return: SPY {replay.contributions_pp.SPY.toFixed(2)} percentage points · TLT{" "}
              {replay.contributions_pp.TLT.toFixed(2)} percentage points. Daily return correlation:{" "}
              {replay.correlation?.toFixed(3) ?? "Unavailable (constant returns)"}.
            </p>
            {(["SPY", "TLT"] as const).map((s) => (
              <p key={s}>
                <a href={replay.sources[s]} target="_blank" rel="noreferrer" className="underline">
                  Yahoo Finance · {s} historical data
                </a>{" "}
                · Retrieved {replay.retrieved[s]} · USD
              </p>
            ))}
          </div>
        </details>
      </CardContent>
    </Card>
  );
}
