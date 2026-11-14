"use client";

import { useId } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { formatCurrency } from "@/lib/utils";

export type PricePoint = { time: number; Close: number };

const config = { Close: { label: "Closing price", color: "currentColor" } };

export function PriceChart({
  tone,
  points,
  period,
  currency,
}: {
  tone: string;
  points: PricePoint[];
  period: string;
  currency: string | null;
}) {
  const gradient = useId();
  const monthly = ["3mo", "6mo", "ytd", "1y"].includes(period);
  const daily = period === "3y" || period === "5y";
  const axisDate = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    ...(period === "1d"
      ? { hour: "numeric", minute: "2-digit" }
      : daily
        ? { year: "numeric" }
        : monthly
          ? { month: "short" }
          : { month: "short", day: "numeric" }),
  });
  const tooltipDate = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    dateStyle: "medium",
    timeStyle: daily ? undefined : "short",
  });

  const ticks =
    period === "1d" || period === "1mo"
      ? undefined
      : points
          .filter(
            (point, index) =>
              index === 0 || axisDate.format(point.time * 1000) !== axisDate.format(points[index - 1].time * 1000),
          )
          .map((point) => point.time);

  return (
    <ChartContainer config={config} className="aspect-auto h-72 w-full sm:h-96">
      <AreaChart accessibilityLayer data={points} margin={{ top: 12, right: 8, bottom: 4 }}>
        <defs>
          <linearGradient id={gradient} className={tone} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity={0.32} />
            <stop offset="100%" stopColor="currentColor" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--border)" strokeOpacity={0.55} />
        <XAxis
          dataKey="time"
          axisLine={false}
          tickLine={false}
          ticks={ticks}
          minTickGap={32}
          tickFormatter={(time) => axisDate.format(time * 1000)}
        />
        <YAxis
          orientation="right"
          tickCount={5}
          domain={["auto", "auto"]}
          axisLine={false}
          tickLine={false}
          width="auto"
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(_, payload) => tooltipDate.format(payload[0].payload.time * 1000)}
              formatter={(value) => (currency ? formatCurrency(Number(value), { currency }) : String(value))}
            />
          }
        />
        <Area
          className={tone}
          baseValue="dataMin"
          fill={`url(#${gradient})`}
          fillOpacity={1}
          dataKey="Close"
          type="linear"
          stroke="currentColor"
          strokeWidth={2}
          dot={points.length === 1}
          isAnimationActive={false}
        />
      </AreaChart>
    </ChartContainer>
  );
}
