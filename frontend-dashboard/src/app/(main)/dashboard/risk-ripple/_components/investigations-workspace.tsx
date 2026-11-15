"use client";

import { ChevronDown, ExternalLink, History, Loader2, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getHistory, pollAlertsScan, triggerAlertsScan, type CombinedScanState } from "@/server/alerts-actions";
import type { AlertMatch, InvestigationHistoryEntry, ScanResponse } from "@/server/riskripple";

import { ATTENTION_META, FindingsCards } from "./findings-cards";
import { InvestigateForm, type Prefill } from "./investigate-form";

const POLL_INTERVAL_MS = 7000;
const EMPTY_SCAN: ScanResponse = {
  alerts: [],
  articles: [],
  investigation_candidates: [],
  confirmed_alerts: [],
  status: "idle",
  last_success_at: null,
  error_message: null,
};

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins === 1) return "1 minute ago";
  if (mins < 60) return `${mins} minutes ago`;
  const hours = Math.round(mins / 60);
  return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
}

function tierLabel(tier: number | null | undefined): string {
  switch (tier) {
    case 1: return "Article discovered";
    case 2: return "Event reported";
    case 3: return "Materially significant";
    case 4: return "Potential portfolio exposure";
    case 5: return "Evidence-supported exposure";
    default: return "Candidate";
  }
}

function SourceBadge({ source }: { source?: "news" | "regulatory" }) {
  return <Badge variant="outline" className="text-xs">{source === "news" ? "News" : "Regulatory"}</Badge>;
}

function MatchAccordionItem({ match, keyId }: { match: AlertMatch; keyId: string }) {
  return (
    <AccordionItem value={keyId}>
      <AccordionTrigger className="gap-2 text-sm hover:no-underline">
        <div className="flex flex-1 flex-wrap items-center gap-2 text-left">
          <Badge variant="secondary">{match.symbol}</Badge>
          <SourceBadge source={match.source} />
          {match.classification_tier != null && (
            <Badge variant="outline" className="text-xs">{tierLabel(match.classification_tier)}</Badge>
          )}
          <span className="font-medium">{match.title ?? match.matched_entity}</span>
        </div>
      </AccordionTrigger>
      <AccordionContent className="flex flex-col gap-2 text-sm">
        {match.document_url && (
          <a
            href={match.document_url}
            target="_blank"
            rel="noreferrer"
            className="flex w-fit items-center gap-1 text-sm font-medium hover:underline"
          >
            Source
            <ExternalLink className="size-3.5" />
          </a>
        )}
        {match.evidence_snippet && (
          <blockquote className="border-border text-muted-foreground border-l-2 pl-3 text-sm italic">
            "{match.evidence_snippet}"
          </blockquote>
        )}
        {match.exposure_mechanism && (
          <p className="text-muted-foreground text-sm">
            <span className="font-medium text-foreground">Mechanism: </span>
            {match.exposure_mechanism}
          </p>
        )}
        {match.recommendation && <p className="text-sm">{match.recommendation}</p>}
      </AccordionContent>
    </AccordionItem>
  );
}

// Rendering every past investigation fully expanded, forever, buried the page under
// repeated full briefings + per-stock findings + evidence for every single past query
// -- confirmed by the user as "turns into a mess" after running just a few. Only the
// newest survives expanded by default; everything older collapses to one line (date,
// tickers, attention verdict, the event text) that expands on click.
function HistoryEntryItem({ entry, defaultOpen }: { entry: InvestigationHistoryEntry; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const attention = entry.result.event_briefing
    ? ATTENTION_META[entry.result.event_briefing.attention_level] ?? ATTENTION_META.INSUFFICIENT_EVIDENCE
    : null;

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="border-border border-b pb-4 last:border-0 last:pb-0">
      <CollapsibleTrigger className="flex w-full flex-wrap items-center gap-2 text-left text-sm hover:underline">
        <ChevronDown className={`size-4 shrink-0 transition-transform ${open ? "" : "-rotate-90"}`} />
        <span className="text-muted-foreground text-xs">{new Date(entry.created_at).toLocaleString()}</span>
        <Badge variant="outline" className="text-xs">{entry.portfolio_holdings.join(", ")}</Badge>
        {attention && <Badge variant={attention.variant} className="text-xs">{attention.label}</Badge>}
        <span className="flex-1 truncate font-medium">{entry.event_description}</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-3">
        <FindingsCards result={entry.result} />
      </CollapsibleContent>
    </Collapsible>
  );
}

type StatusFilter = "all" | "confirmed" | "candidate" | "history";
type SortMode = "priority" | "recency";

export function InvestigationsWorkspace({
  defaultTickers,
  initialPrefill,
}: {
  defaultTickers: string;
  initialPrefill?: Prefill | null;
}) {
  const [state, setState] = useState<CombinedScanState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [history, setHistory] = useState<InvestigationHistoryEntry[] | null>(null);
  const [prefill, setPrefill] = useState<Prefill | null>(initialPrefill ?? null);
  const [formOpen, setFormOpen] = useState(true);
  const formRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef(false);

  const [tickerFilter, setTickerFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortMode, setSortMode] = useState<SortMode>("priority");

  useEffect(() => {
    if (initialPrefill) {
      requestAnimationFrame(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    triggerAlertsScan().then((result) => {
      if (cancelled) return;
      if (!result.ok) setLoadError(result.error);
      else setState(result.data);
    });
    getHistory().then((result) => {
      if (!cancelled && result.ok) setHistory(result.data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!state) return;
    const isScanning = state.news.status === "scanning" || state.regulatory.status === "scanning";
    if (!isScanning) return;
    const interval = setInterval(async () => {
      if (pollingRef.current) return;
      pollingRef.current = true;
      try {
        const result = await pollAlertsScan();
        if (result.ok) {
          setState((prev) => (prev ? { ...prev, news: result.data.news, regulatory: result.data.regulatory } : prev));
        }
      } finally {
        pollingRef.current = false;
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [state?.news.status, state?.regulatory.status]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleReinvestigate(eventDescription: string, tickers: string) {
    setPrefill({ eventDescription, tickers });
    setFormOpen(true);
    requestAnimationFrame(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  async function refreshHistory() {
    const result = await getHistory();
    if (result.ok) setHistory(result.data);
  }

  if (loadError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">{loadError}</p>
        </CardContent>
      </Card>
    );
  }

  const news = state?.news ?? EMPTY_SCAN;
  const regulatory = state?.regulatory ?? EMPTY_SCAN;
  const confirmed = [...news.confirmed_alerts, ...regulatory.confirmed_alerts];
  const candidates = [...news.investigation_candidates, ...regulatory.investigation_candidates];
  const lastSuccess = [news.last_success_at, regulatory.last_success_at].filter(Boolean).sort().pop() ?? null;
  const anyScanning = news.status === "scanning" || regulatory.status === "scanning";

  const tickerSet = new Set<string>();
  for (const m of [...confirmed, ...candidates]) if (m.symbol) tickerSet.add(m.symbol);
  for (const h of history ?? []) for (const t of h.portfolio_holdings) tickerSet.add(t);
  const tickers = [...tickerSet].sort();

  function matchesTicker(symbol: string | undefined, holdings?: string[]) {
    if (tickerFilter === "all") return true;
    if (symbol) return symbol === tickerFilter;
    return holdings?.includes(tickerFilter) ?? false;
  }

  const sortMatches = (items: AlertMatch[]) =>
    [...items].sort((a, b) => {
      if (sortMode === "priority") return (b.classification_tier ?? 0) - (a.classification_tier ?? 0);
      return 0; // recency has no per-match timestamp finer than the scan itself
    });

  const filteredConfirmed = statusFilter === "all" || statusFilter === "confirmed"
    ? sortMatches(confirmed.filter((m) => matchesTicker(m.symbol)))
    : [];
  const filteredCandidates = statusFilter === "all" || statusFilter === "candidate"
    ? sortMatches(candidates.filter((m) => matchesTicker(m.symbol)))
    : [];
  const filteredHistory = statusFilter === "all" || statusFilter === "history"
    ? (history ?? []).filter((h) => matchesTicker(undefined, h.portfolio_holdings))
    : [];

  return (
    <div className="flex flex-col gap-4">
      <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-xs">
        <span>Last updated: {timeAgo(lastSuccess)}</span>
        {(news.status === "error" || regulatory.status === "error") && lastSuccess && (
          <span className="text-amber-600 dark:text-amber-400">
            · Last refresh failed, showing previous results ({news.error_message || regulatory.error_message})
          </span>
        )}
      </div>

      {!state && !loadError && (
        <Card>
          <CardContent className="flex items-center gap-2 pt-6 text-sm">
            <Loader2 className="size-4 animate-spin" />
            Starting first scan…
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Select value={tickerFilter} onValueChange={setTickerFilter}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="Stock" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All holdings</SelectItem>
            {tickers.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-[180px]"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="confirmed">Confirmed alerts</SelectItem>
            <SelectItem value="candidate">Candidates</SelectItem>
            <SelectItem value="history">Past investigations</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
          <SelectTrigger className="w-[150px]"><SelectValue placeholder="Sort" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="priority">Priority first</SelectItem>
            <SelectItem value="recency">Most recent</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {state && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="size-4" />
              Portfolio Alerts & Investigations
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {anyScanning && (
              <div className="text-muted-foreground flex items-center gap-2 text-xs">
                <Loader2 className="size-3.5 animate-spin" />
                Scanning for updates…
              </div>
            )}

            <div>
              <h3 className="mb-1 text-sm font-medium">Confirmed portfolio exposure alerts</h3>
              {filteredConfirmed.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No confirmed alerts right now — checked real Federal Register documents and real recent news
                  against your actual holdings.
                </p>
              ) : (
                <Accordion type="multiple">
                  {filteredConfirmed.map((m, i) => (
                    <MatchAccordionItem key={`confirmed-${i}`} match={m} keyId={`confirmed-${i}`} />
                  ))}
                </Accordion>
              )}
            </div>

            <div>
              <h3 className="mb-1 text-sm font-medium">
                Investigation candidates <span className="text-muted-foreground font-normal">(plausible, not yet confirmed)</span>
              </h3>
              {filteredCandidates.length === 0 ? (
                <p className="text-muted-foreground text-sm">No open candidates for this filter.</p>
              ) : (
                <Accordion type="multiple">
                  {filteredCandidates.map((m, i) => (
                    <MatchAccordionItem key={`candidate-${i}`} match={m} keyId={`candidate-${i}`} />
                  ))}
                </Accordion>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {(statusFilter === "all" || statusFilter === "history") && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="size-4" />
              Previously completed manual investigations
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {history === null ? (
              <p className="text-muted-foreground text-sm">Loading…</p>
            ) : filteredHistory.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No past manual investigations for this filter yet — run one below.
              </p>
            ) : (
              filteredHistory.map((h, i) => (
                <HistoryEntryItem key={h.created_at} entry={h} defaultOpen={i === 0} />
              ))
            )}
          </CardContent>
        </Card>
      )}

      <div ref={formRef}>
        <Collapsible open={formOpen} onOpenChange={setFormOpen}>
          <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-sm hover:underline">
            <ChevronDown className="size-4" />
            Ask about a specific event
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <InvestigateForm defaultTickers={defaultTickers} prefill={prefill} onComplete={refreshHistory} />
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
