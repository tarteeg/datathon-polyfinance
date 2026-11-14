import Link from "next/link";
import type { ReactNode } from "react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export const periodLabels: Record<string, string> = {
  "1d": "Today",
  "5d": "Past 5 days",
  "1mo": "Past month",
  "3mo": "Past 3 months",
  "6mo": "Past 6 months",
  ytd: "Year to date",
  "1y": "Past year",
  "3y": "Past 3 years",
  "5y": "Past 5 years",
};

export function PricePanel({
  symbol,
  period,
  name,
  market,
  price,
  children,
}: {
  symbol: string;
  period: string;
  name?: ReactNode;
  market?: ReactNode;
  price?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="flex flex-wrap items-baseline gap-x-3">
            <span className="text-3xl font-bold tracking-tight">{symbol}</span>
            <span className="text-lg font-medium text-muted-foreground">{name}</span>
          </h1>
          <div className="text-xs text-muted-foreground">{market}</div>
        </div>
        <div className="sm:text-right">
          <div className="flex flex-wrap items-baseline gap-2 font-semibold tabular-nums sm:justify-end">{price}</div>
          <p className="text-xs text-muted-foreground">{periodLabels[period]}</p>
        </div>
      </CardHeader>
      <CardContent>
        <nav
          aria-label="Price history period"
          className="mb-1 flex justify-between gap-1 overflow-x-auto border-t py-2"
        >
          {Object.keys(periodLabels).map((option) => (
            <Link
              key={option}
              prefetch={false}
              scroll={false}
              aria-current={option === period ? "page" : undefined}
              href={`/dashboard/stock/${encodeURIComponent(symbol)}?period=${option}`}
              className={buttonVariants({
                size: "sm",
                variant: option === period ? "secondary" : "ghost",
                className: "rounded-full",
              })}
            >
              {option.replace("mo", "m").toUpperCase()}
            </Link>
          ))}
        </nav>
        {children}
      </CardContent>
    </Card>
  );
}
