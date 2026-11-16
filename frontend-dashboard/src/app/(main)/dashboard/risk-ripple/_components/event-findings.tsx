import { ArrowDownRight, ArrowUpRight, BookOpen, ChevronDown, ExternalLink, Layers2, Minus } from "lucide-react";

import { Badge } from "@/components/ui/badge";

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
export type EventResult = {
  investor_note?: { ticker: string; interpretation: string; question: string };
  id: string;
  title: string;
  published: string;
  event_date: string | null;
  exposed_weight: number | null;
  holdings: Position[];
  outside: Position[];
};

const percent = new Intl.NumberFormat(undefined, { style: "percent", maximumFractionDigits: 1 });
export const date = (value: string) =>
  new Date(value.length === 10 ? value + "T12:00:00" : value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
const disclosure =
  "group flex min-h-8 cursor-pointer list-none items-center gap-2 rounded-sm py-1 text-sm font-medium focus-visible:outline-ring [&::-webkit-details-marker]:hidden";
const chevron = "size-4 shrink-0 text-muted-foreground in-[details[open]>summary]:rotate-180";

function PositionFinding({ position }: { position: Position }) {
  const pressure = position.direction === "potential pressure";
  const benefit = position.direction === "potential benefit";
  const Direction = pressure ? ArrowDownRight : benefit ? ArrowUpRight : Minus;
  return (
    <li className="flex min-w-0 flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="rounded bg-muted px-2 py-0.5 font-mono text-sm font-semibold">{position.ticker}</span>
        {position.direction && (
          <Badge variant={pressure ? "destructive" : "secondary"}>
            <Direction aria-hidden="true" />
            {position.direction}
          </Badge>
        )}
        <span className="text-xs text-muted-foreground">
          {[
            position.relationship,
            position.watchlist
              ? "Watchlist"
              : position.weight != null && percent.format(position.weight) + " of portfolio",
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
      </div>
      {position.explanation && <p className="max-w-prose text-sm leading-relaxed">{position.explanation}</p>}
      {!!position.citations?.length && (
        <details>
          <summary className={disclosure}>
            <BookOpen className="size-3.5" aria-hidden="true" />
            Sources ({position.citations.length})<ChevronDown className="size-3.5" aria-hidden="true" />
          </summary>
          <ul className="mt-2 grid gap-3 border-l-2 pl-3">
            {position.citations.map((source, index) => (
              <li key={`${source.url}-${index}`} className="max-w-prose text-sm">
                <blockquote className="text-muted-foreground">“{source.quote}”</blockquote>
                <a
                  className="mt-1 inline-flex items-center gap-1 underline underline-offset-4"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {source.kind === "article"
                    ? `Publisher (${source.coverage ?? "unknown coverage"})`
                    : `${source.ticker} filing`}
                  {source.date && ` · ${date(source.date)}`}
                  <ExternalLink className="size-3" aria-hidden="true" />
                </a>
              </li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}

export function EventCard({ event, persona, expanded }: { event: EventResult; persona?: string; expanded: boolean }) {
  const linked = event.holdings.filter((p) => p.status === "supported" || (!p.status && !!p.explanation));
  const other = event.holdings.filter((p) => !linked.includes(p));
  const incomplete = other.filter((position) => position.status === "incomplete").length;
  return (
    <article className="overflow-hidden rounded-xl border bg-card text-card-foreground">
      <details open={expanded} className="group/event">
        <summary className="grid cursor-pointer list-none gap-2 p-4 hover:bg-muted/30 focus-visible:outline-ring sm:p-5 [&::-webkit-details-marker]:hidden">
          <span className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            Latest coverage · {date(event.published)}
            <ChevronDown className="size-4 shrink-0 group-open/event:rotate-180" aria-hidden="true" />
          </span>
          <h3 className="max-w-[52ch] text-pretty text-lg font-semibold leading-snug tracking-tight">{event.title}</h3>
          <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {linked.map((p) => (
              <Badge key={p.ticker} variant="outline">
                {p.ticker}
              </Badge>
            ))}
            {event.exposed_weight != null && (
              <span className="inline-flex items-center gap-1">
                <Layers2 className="size-3.5" aria-hidden="true" />
                {percent.format(event.exposed_weight)} of portfolio linked
              </span>
            )}
          </span>
        </summary>
        <div className="flex flex-col gap-4 border-t px-4 py-4 sm:px-5">
          {event.investor_note && persona && (
            <div className="grid gap-1 rounded-md border-l-2 border-primary bg-muted/50 px-3 py-2 text-sm">
              <h4 className="font-semibold">
                <span className="capitalize">{persona}</span>’s perspective · {event.investor_note.ticker}
              </h4>
              <p>{event.investor_note.interpretation}</p>
              <p className="text-muted-foreground">{event.investor_note.question}</p>
            </div>
          )}
          {!!linked.length && (
            <section className="grid gap-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Affected holdings
              </h4>
              <ul className="grid gap-4">
                {linked.map((p) => (
                  <PositionFinding key={p.ticker} position={p} />
                ))}
              </ul>
            </section>
          )}
          {!!event.outside.length && (
            <details className="border-t pt-2">
              <summary className={disclosure}>
                <ChevronDown className={chevron} aria-hidden="true" />
                <span>
                  Other affected S&amp;P 500 companies ({event.outside.length}){" "}
                  <span className="ml-1 inline-block font-mono text-xs text-muted-foreground">
                    {event.outside.map((p) => p.ticker).join(" · ")}
                  </span>
                </span>
              </summary>
              <ul className="mt-3 grid gap-4">
                {event.outside.map((p) => (
                  <PositionFinding key={p.ticker} position={p} />
                ))}
              </ul>
            </details>
          )}
          {!!other.length && (
            <details className="border-t pt-2">
              <summary className={disclosure}>
                <ChevronDown className={chevron} aria-hidden="true" />
                <span>
                  Other holdings reviewed ({other.length}){" "}
                  {incomplete > 0 && (
                    <span className="ml-1 inline-block text-xs text-muted-foreground">
                      {incomplete} with incomplete evidence
                    </span>
                  )}
                </span>
              </summary>
              <ul className="mt-2 grid gap-2 text-sm">
                {other.map((p) => (
                  <li key={p.ticker} className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <span className="font-mono font-medium">
                      {p.ticker}{" "}
                      <span className="font-sans text-xs text-muted-foreground">
                        {p.watchlist ? "Watchlist" : p.weight != null && percent.format(p.weight)}
                      </span>
                    </span>
                    <span className="text-muted-foreground">
                      {p.status === "incomplete" ? "Incomplete evidence" : "No supported connection"}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {event.event_date && <p className="text-xs text-muted-foreground">Event date · {date(event.event_date)}</p>}
        </div>
      </details>
    </article>
  );
}
