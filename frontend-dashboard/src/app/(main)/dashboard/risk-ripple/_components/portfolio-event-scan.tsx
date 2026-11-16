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
  investor_note?: { ticker: string; interpretation: string; question: string };
  id: string;
  title: string;
  published: string;
  event_date: string | null;
  exposed_weight: number | null;
  holdings: Position[];
  outside: Position[];
};
type Report = {
  persona?: string;
  start: string;
  end: string;
  screened: number;
  shortlisted: number;
  available: number;
  weighted: boolean;
  quotes_checked?: string;
  events: EventResult[];
  warnings: string[];
};
type Step = {
  key: string;
  title: string;
  detail: string;
  status: "running" | "completed" | "reused" | "unavailable";
  updated: string;
  done?: number | null;
  total?: number | null;
};
type Activity = {
  id: string;
  steps: Step[];
  partial: EventResult[];
  first_finding_ms: number | null;
  elapsed_ms: number;
  model_calls: number;
};
type Scan = {
  activity?: Activity | null;
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
          <summary className="text-muted-foreground cursor-pointer">Sources ({position.citations.length})</summary>
          <ul className="flex flex-col gap-2 py-2">
            {position.citations.map((source) => (
              <li key={`${source.url}-${source.quote}`}>
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

function EventCard({ event, persona }: { event: EventResult; persona?: string }) {
  return (
    <article className="flex w-full flex-col gap-3 border-t pt-4">
      <h3 className="font-semibold">{event.title}</h3>
      <p className="text-muted-foreground text-sm">
        {event.event_date && `Event date ${event.event_date} · `}Latest coverage {date(event.published)}
        {event.exposed_weight !== null &&
          ` · Linked positions represent ${percent.format(event.exposed_weight)} of your portfolio`}
      </p>
      {event.investor_note && persona && (
        <div className="flex flex-col gap-1 text-sm">
          <h4 className="font-medium">
            <span className="capitalize">{persona}</span>’s perspective · {event.investor_note.ticker}
          </h4>
          <p>{event.investor_note.interpretation}</p>
          <p>{event.investor_note.question}</p>
        </div>
      )}
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
  );
}

const clockTime = (value: string) => new Date(value).toLocaleTimeString();
const duration = (ms: number) => (ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);

function ScanActivity({ activity, running }: { activity: Activity; running: boolean }) {
  const current = [...activity.steps].reverse().find((step) => step.status === "running");
  return (
    <div className="w-full space-y-3">
      {running && (
        <p role="status" className="text-sm font-medium">
          {current?.title ?? "Checking portfolio news"}
          {current?.total != null && ` · ${current.done} of ${current.total}`}
          {current?.detail && ` · ${current.detail}`}
        </p>
      )}
      <details className="w-full rounded-md border p-3">
        <summary className="cursor-pointer text-sm font-medium">Investigation activity</summary>
        <ol className="mt-3 space-y-3 border-l pl-4">
          {activity.steps.map((step) => (
            <li key={step.key} className="text-sm">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-medium">{step.title}</span>
                <span className="capitalize">{step.status}</span>
                <time className="text-muted-foreground text-xs" dateTime={step.updated}>
                  {clockTime(step.updated)}
                </time>
              </div>
              {step.total != null && (
                <span>
                  {step.done} of {step.total} ·{" "}
                </span>
              )}
              {step.detail}
            </li>
          ))}
        </ol>
        <p className="text-muted-foreground mt-3 border-t pt-2 text-xs">
          {activity.first_finding_ms != null && `First verified finding in ${duration(activity.first_finding_ms)} · `}
          {duration(activity.elapsed_ms)} elapsed · {activity.model_calls} Bedrock{" "}
          {activity.model_calls === 1 ? "call" : "calls"}
        </p>
      </details>
    </div>
  );
}

export function PortfolioEventScan({ hasHoldings }: { hasHoldings: boolean }) {
  const [scan, setScan] = useState<Scan>();
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const running = scan?.status === "scanning";
  useEffect(() => {
    if (!hasHoldings || starting) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const state = await request("GET", controller.signal);
        if (controller.signal.aborted) return;
        setScan(state);
        setError("");
        if (state.status === "scanning") timer = setTimeout(poll, 1500);
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
  }, [running, hasHoldings, starting]);

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
  let buttonText = report ? "Check for updates" : "Scan my portfolio";
  if (running) buttonText = "Investigation in progress";
  if (starting) buttonText = "Checking for updates…";
  return (
    <Card>
      <CardHeader>
        <CardTitle>Events affecting your portfolio</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-4">
        <p className="text-muted-foreground text-sm">
          Search 30 days of news for business developments that affect your holdings and related companies.
        </p>
        <Button disabled={!hasHoldings || starting || running || (!scan && !error)} onClick={start}>
          {buttonText}
        </Button>
        {!hasHoldings && <p>Add a holding or watchlist entry to start a scan.</p>}
        {(error || scan?.error) && <p role="alert">{error || scan?.error}</p>}
        {scan?.activity && <ScanActivity activity={scan.activity} running={running} />}
        {scan?.status !== "idle" && !!scan?.activity?.partial.length && (
          <section className="w-full space-y-3" aria-label="Verified findings so far">
            <h3 className="font-semibold">Verified so far ({scan.activity.partial.length})</h3>
            {scan.activity.partial.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </section>
        )}
        {report && (
          <>
            {(running || starting || scan?.status === "error") && (
              <h3 className="font-semibold">Previous completed report</h3>
            )}
            <p className="text-muted-foreground text-sm">
              {scan?.updated && `Last completed ${date(scan.updated)} at ${clockTime(scan.updated)}. `}
              {date(report.start)} – {date(report.end)} · Screened {report.screened} of {report.available} events.
              Shortlisted {report.shortlisted} for source review.{" "}
              {report.weighted
                ? "Ranked using business impact and current position weights."
                : "Ranked by business relevance. Comparable position values were unavailable."}
              {report.weighted && report.quotes_checked && ` Quotes checked at ${clockTime(report.quotes_checked)}.`}
            </p>
            {report.warnings.map((w) => (
              <p key={w} className="text-sm">
                {w}
              </p>
            ))}
            {!report.events.length && <p>No material portfolio connection was verified in the events assessed.</p>}
            {report.events.map((event) => (
              <EventCard key={event.id} event={event} persona={report.persona} />
            ))}
          </>
        )}
      </CardContent>
    </Card>
  );
}
