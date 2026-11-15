import Link from "next/link";
import type { ReactNode } from "react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const periodLabels: Record<string, string> = {
  "1d": "Past trading day",
  "5d": "Past 5 days",
  mtd: "Month to date",
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
  action,
  children,
}: {
  symbol: string;
  period: string;
  name?: ReactNode;
  market?: ReactNode;
  price?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex min-w-0 flex-col gap-5" aria-labelledby="stock-heading">
      <header className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-md bg-muted px-2 py-1 font-mono font-semibold text-foreground">{symbol}</span>
            {market}
          </div>
          <h1 id="stock-heading" className="text-3xl font-semibold tracking-tight sm:text-4xl">
            {name ?? symbol}
          </h1>
        </div>
        {price && <div className="flex flex-col gap-1 tabular-nums sm:items-end">{price}</div>}
      </header>
      <Card>
        <CardHeader className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-lg">Price history</CardTitle>
          {action}
        </CardHeader>
        <CardContent className="min-w-0">
          <nav
            aria-label="Price history period"
            className="mb-4 grid grid-cols-5 gap-1 rounded-lg bg-muted/60 p-1 sm:inline-flex"
          >
            {Object.entries(periodLabels).map(([option, label]) => (
              <Link
                key={option}
                prefetch={false}
                scroll={false}
                aria-label={label}
                title={label}
                aria-current={option === period ? "page" : undefined}
                href={`/dashboard/stock/${encodeURIComponent(symbol)}?period=${option}`}
                className={buttonVariants({
                  size: "sm",
                  variant: option === period ? "default" : "ghost",
                  className: "h-8 min-w-0 px-2 tabular-nums sm:min-w-10",
                })}
              >
                {option.replace("mo", "m").toUpperCase()}
              </Link>
            ))}
          </nav>
          {children}
        </CardContent>
      </Card>
    </section>
  );
}
