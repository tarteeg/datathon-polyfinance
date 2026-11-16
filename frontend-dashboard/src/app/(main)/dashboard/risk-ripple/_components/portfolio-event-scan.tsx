"use client";

import { CalendarDays, ListFilter, Newspaper, Radar, ScanLine, ShieldCheck, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { type EventResult, EventCard, date } from "./event-findings";
import { type Activity, ScanActivity, clockTime } from "./scan-activity";

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
type Scan = {
  activity?: Activity | null;
  status: "idle" | "scanning" | "error";
  updated: string | null;
  error: string | null;
  result: Report | null;
};

async function request(method: "GET" | "POST", signal?: AbortSignal): Promise<Scan> {
  const response = await fetch("/api/portfolio-events", { method, cache: "no-store", signal });
  if (!response.ok) throw new Error("Could not reach the portfolio scan. Please try again.");
  return response.json();
}

export function PortfolioEventScan({ positionCount }: { positionCount: number }) {
  const hasHoldings = positionCount > 0;
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
  if (starting) buttonText = "Checking for updates…";
  const activity = scan?.activity;
  const partial = scan?.status !== "idle" ? (activity?.partial ?? []) : [];
  const previous = !!report && (running || starting || scan?.status === "error");
  const screen = activity?.steps.find((step) => step.key === "screen");
  const errorMessage = error || scan?.error;
  const metrics = [
    { label: "Events screened", value: (!previous ? report?.screened : undefined) ?? screen?.done, icon: Newspaper },
    { label: "Positions", value: positionCount, icon: ListFilter },
    {
      label: "Verified events",
      value: previous || !report ? activity?.partial.length : report.events.length,
      icon: ShieldCheck,
    },
  ];
  return (
    <section aria-label="Portfolio news investigation" className="@container flex min-w-0 flex-col gap-5">
      <div className="overflow-hidden rounded-xl border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-4 bg-primary px-5 py-5 text-primary-foreground sm:px-6">
          <div className="flex min-w-0 items-start gap-3">
            <span className="shrink-0 rounded-xl border border-current/25 p-2.5">
              <Radar aria-hidden="true" className="size-6" />
            </span>
            <div className="min-w-0">
              <h2 className="text-xl font-semibold leading-tight tracking-tight">Portfolio impact scan</h2>
              <p className="mt-1 max-w-prose text-sm opacity-80">
                Investigate the past 30 days of news for effects on your holdings and related companies.
              </p>
            </div>
          </div>
          {running ? (
            <span role="status" className="inline-flex items-center gap-2 text-sm font-medium">
              <Spinner aria-hidden="true" className="motion-reduce:animate-none" />
              Investigating
            </span>
          ) : (
            <Button
              size="lg"
              variant="secondary"
              disabled={!hasHoldings || starting || (!scan && !error)}
              onClick={start}
            >
              {starting ? (
                <Spinner aria-hidden="true" data-icon="inline-start" />
              ) : (
                <ScanLine aria-hidden="true" data-icon="inline-start" />
              )}
              {buttonText}
            </Button>
          )}
        </div>
        <dl className="grid grid-cols-3 divide-x">
          {metrics.map(({ label, value, icon: Icon }) => (
            <div key={label} className="flex flex-col justify-between gap-2 p-3 sm:px-6 sm:py-4">
              <dt className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <Icon className="hidden size-4 sm:block" aria-hidden="true" />
                {label}
              </dt>
              <dd className="text-2xl font-semibold leading-none tracking-tight tabular-nums">
                {typeof value === "number" ? value.toLocaleString() : "—"}
              </dd>
            </div>
          ))}
        </dl>
      </div>
      {!hasHoldings && (
        <p className="text-sm text-muted-foreground">Add a holding or watchlist entry to start a scan.</p>
      )}
      {errorMessage && (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}
      <div
        className={activity ? "grid min-w-0 items-start gap-5 @min-[52rem]:grid-cols-[minmax(0,1fr)_18rem]" : "min-w-0"}
      >
        {activity && (
          <aside className="min-w-0 @min-[52rem]:col-start-2 @min-[52rem]:row-start-1">
            <ScanActivity activity={activity} running={running} />
          </aside>
        )}
        <div className="grid min-w-0 gap-5 @min-[52rem]:col-start-1 @min-[52rem]:row-start-1">
          {partial.length > 0 && (
            <section className="grid gap-3" aria-label="Verified findings so far">
              <h2 className="text-lg font-semibold tracking-tight">Verified so far ({partial.length})</h2>
              {partial.map((event, i) => (
                <EventCard key={event.id} event={event} expanded={i === 0} />
              ))}
            </section>
          )}
          {running && !partial.length && (
            <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
              Verified findings will appear here as the investigation checks its sources.
            </p>
          )}
          {report && (
            <section className="grid gap-3" aria-label="Completed report">
              <h2 className="text-lg font-semibold tracking-tight">
                {previous ? "Previous completed report" : "Portfolio findings"}
              </h2>
              <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                <CalendarDays className="size-3.5" aria-hidden="true" />
                {date(report.start)} – {date(report.end)} · {report.screened.toLocaleString()} of{" "}
                {report.available.toLocaleString()} screened · {report.shortlisted} shortlisted
              </p>
              <details className="text-xs text-muted-foreground">
                <summary className="w-fit cursor-pointer">Ranking details</summary>
                <p className="mt-2 max-w-prose">
                  {report.weighted
                    ? "Ranked using business impact and position weights."
                    : "Ranked by business relevance. Comparable position values were unavailable."}
                  {report.weighted &&
                    report.quotes_checked &&
                    ` Quotes checked at ${clockTime(report.quotes_checked)}.`}
                  {scan?.updated && ` Completed ${date(scan.updated)} at ${clockTime(scan.updated)}.`}
                </p>
              </details>
              {report.warnings.map((w) => (
                <Alert key={w}>
                  <TriangleAlert />
                  <AlertDescription>{w}</AlertDescription>
                </Alert>
              ))}
              {!report.events.length && (
                <p className="text-sm">No material portfolio connection was verified in the events assessed.</p>
              )}
              {report.events.map((event, i) => (
                <EventCard key={event.id} event={event} persona={report.persona} expanded={i === 0 && !previous} />
              ))}
            </section>
          )}
        </div>
      </div>
    </section>
  );
}
