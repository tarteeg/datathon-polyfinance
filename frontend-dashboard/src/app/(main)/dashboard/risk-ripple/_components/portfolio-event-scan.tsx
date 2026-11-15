"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Evidence = {
  kind: "filing" | "article";
  coverage?: string;
  ticker?: string;
  url: string;
  date?: string;
  quote: string;
};
type Position = {
  ticker: string;
  watchlist?: boolean;
  weight?: number | null;
  status?: string;
  relationship?: string;
  direction?: string;
  explanation?: string;
  citations?: Evidence[];
};
type EventResult = {
  id: string;
  title: string;
  published: string;
  event_date: string | null;
  exposed_weight: number | null;
  holdings: Position[];
  outside: Position[];
};
type Report = {
  start: string;
  end: string;
  screened: number;
  shortlisted: number;
  available: number;
  weighted: boolean;
  events: EventResult[];
  warnings: string[];
};
type Scan = {
  status: "idle" | "scanning" | "error";
  updated: string | null;
  error: string | null;
  result: Report | null;
};

const percent = new Intl.NumberFormat(undefined, { style: "percent", maximumFractionDigits: 1 });
const date = (value: string) =>
  new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

async function request(method: "GET" | "POST", signal?: AbortSignal): Promise<Scan> {
  const response = await fetch("/api/portfolio-events", { method, cache: "no-store", signal });
  if (!response.ok) throw new Error("Could not reach the portfolio scan. Please try again.");
  return response.json();
}

function PositionFinding({ position }: { position: Position }) {
  return (
    <li className="flex flex-col gap-1">
      <div>
        <strong>{position.ticker}</strong>
        {position.watchlist
          ? " · Watchlist"
          : position.weight != null && ` · ${percent.format(position.weight)} of portfolio`}
        {position.direction && ` · ${position.direction} (${position.relationship})`}
      </div>
      <p className="text-sm">
        {position.explanation ??
          (position.status === "incomplete" ? "Evidence was incomplete." : "No supported connection found.")}
      </p>
      {!!position.citations?.length && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">Sources ({position.citations.length})</summary>
          <ul className="flex flex-col gap-2 py-2">
            {position.citations.map((source, i) => (
              <li key={i}>
                <q>{source.quote}</q>{" "}
                <a className="underline" href={source.url} target="_blank" rel="noreferrer">
                  {source.kind === "article"
                    ? `Publisher (${source.coverage ?? "unknown coverage"})`
                    : `${source.ticker} filing`}
                  {source.date && ` · ${date(source.date)}`}
                </a>
              </li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}

export function PortfolioEventScan({ hasHoldings }: { hasHoldings: boolean }) {
  const [scan, setScan] = useState<Scan>();
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const running = scan?.status === "scanning";
  useEffect(() => {
    if (!hasHoldings) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const state = await request("GET", controller.signal);
        if (controller.signal.aborted) return;
        setScan(state);
        setError("");
        if (state.status === "scanning") timer = setTimeout(poll, 4000);
      } catch {
        if (controller.signal.aborted) return;
        setError("Could not load the scan status.");
        if (running) timer = setTimeout(poll, 8000);
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [running, hasHoldings]);

  async function start() {
    setStarting(true);
    setError("");
    try {
      setScan(await request("POST"));
    } catch {
      setError("Could not start the scan. Please try again.");
    } finally {
      setStarting(false);
    }
  }

  const report = scan?.result;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Events affecting your portfolio</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-4">
        <p className="text-sm text-muted-foreground">
          Search 30 days of news for business developments that affect your holdings and related companies.
        </p>
        <Button disabled={!hasHoldings || starting || running || (!scan && !error)} onClick={start}>
          {running || starting ? "Scanning portfolio…" : "Scan my portfolio"}
        </Button>
        {!hasHoldings && <p>Add a holding or watchlist entry to start a scan.</p>}
        {(error || scan?.error) && <p role="alert">{error || scan?.error}</p>}
        {running && <p role="status">Researching events. You can return to this page while the scan runs.</p>}
        {report && (
          <>
            <p className="text-sm text-muted-foreground">
              {date(report.start)} – {date(report.end)} · Screened {report.screened} of {report.available} events.
              Shortlisted {report.shortlisted} for source review.{" "}
              {report.weighted
                ? "Ranked using business impact and current position weights."
                : "Ranked by business relevance. Comparable position values were unavailable."}
            </p>
            {report.warnings.map((w) => (
              <p key={w} className="text-sm">
                {w}
              </p>
            ))}
            {!report.events.length && <p>No material portfolio connection was verified in the events assessed.</p>}
            {report.events.map((event) => (
              <article className="flex w-full flex-col gap-3 border-t pt-4" key={event.id}>
                <h3 className="font-semibold">{event.title}</h3>
                <p className="text-sm text-muted-foreground">
                  {event.event_date && `Event date ${event.event_date} · `}Latest coverage {date(event.published)}
                  {event.exposed_weight !== null &&
                    ` · Linked positions represent ${percent.format(event.exposed_weight)} of your portfolio`}
                </p>
                <h4 className="text-sm font-medium">Your portfolio</h4>
                <ul className="flex flex-col gap-3">
                  {event.holdings.map((p) => (
                    <PositionFinding key={p.ticker} position={p} />
                  ))}
                </ul>
                {!!event.outside.length && (
                  <>
                    <h4 className="text-sm font-medium">Other affected S&amp;P 500 companies</h4>
                    <ul className="flex flex-col gap-3">
                      {event.outside.map((p) => (
                        <PositionFinding key={p.ticker} position={p} />
                      ))}
                    </ul>
                  </>
                )}
              </article>
            ))}
          </>
        )}
      </CardContent>
    </Card>
  );
}
