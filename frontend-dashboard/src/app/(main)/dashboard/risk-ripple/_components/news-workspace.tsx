"use client";

import { ExternalLink, Loader2, Newspaper } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { pollAlertsScan, triggerAlertsScan, type CombinedScanState } from "@/server/alerts-actions";
import type { NewsArticle, ScanResponse } from "@/server/riskripple";

const POLL_INTERVAL_MS = 7000;
const PAGE_SIZE = 12;
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

const PUBLISHER_NAMES: Record<string, string> = {
  "seekingalpha.com": "Seeking Alpha",
  "benzinga.com": "Benzinga",
  "www.benzinga.com": "Benzinga",
  "marketwatch.com": "MarketWatch",
  "www.marketwatch.com": "MarketWatch",
  "reuters.com": "Reuters",
  "www.reuters.com": "Reuters",
  "bloomberg.com": "Bloomberg",
  "www.bloomberg.com": "Bloomberg",
  "cnbc.com": "CNBC",
  "www.cnbc.com": "CNBC",
};

function publisherFromUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    const hostname = new URL(url).hostname;
    return PUBLISHER_NAMES[hostname] ?? hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function looksNonEnglish(title: string): boolean {
  const nonAscii = [...title].filter((c) => c.charCodeAt(0) > 127).length;
  return title.length > 0 && nonAscii / title.length > 0.15;
}

type PriorityFilter = "all" | "high" | "low";
type SortMode = "priority" | "newest";

// Lightweight category derived from the article's own matched signal -- not a new
// tagging system, just a label for whatever classification tier/relationship it
// already has from the existing pipeline.
function categoryFor(article: NewsArticle, priority: number): string {
  if (priority >= 100) return "Confirmed exposure";
  if (priority >= 50) return "Investigation candidate";
  return "General";
}

function priorityFor(article: NewsArticle, news: ScanResponse): number {
  for (const m of news.confirmed_alerts) {
    if ((m.document_url ?? m.title) === (article.url ?? article.title)) return 100 + (m.classification_tier ?? 0);
  }
  for (const m of news.investigation_candidates) {
    if ((m.document_url ?? m.title) === (article.url ?? article.title)) return 50 + (m.classification_tier ?? 0);
  }
  return 0;
}

export function NewsWorkspace({ onInvestigate }: { onInvestigate: (article: NewsArticle) => void }) {
  const [state, setState] = useState<CombinedScanState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const pollingRef = useRef(false);

  const [tickerFilter, setTickerFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");
  const [sortMode, setSortMode] = useState<SortMode>("priority");
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancelled = false;
    triggerAlertsScan().then((result) => {
      if (cancelled) return;
      if (!result.ok) setLoadError(result.error);
      else setState(result.data);
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

  const news = state?.news ?? EMPTY_SCAN;
  const anyScanning = news.status === "scanning" || state?.regulatory.status === "scanning";

  const withPriority = useMemo(
    () => news.articles.map((a) => ({ article: a, priority: priorityFor(a, news) })),
    [news],
  );

  const tickers = useMemo(() => {
    const set = new Set<string>();
    for (const a of news.articles) if (a.ticker) set.add(a.ticker);
    return [...set].sort();
  }, [news.articles]);

  const filtered = useMemo(() => {
    let items = withPriority;
    if (tickerFilter !== "all") items = items.filter((x) => x.article.ticker === tickerFilter);
    if (priorityFilter === "high") items = items.filter((x) => x.priority >= 50);
    if (priorityFilter === "low") items = items.filter((x) => x.priority < 50);
    items = [...items].sort((a, b) => {
      if (sortMode === "priority") {
        if (a.priority !== b.priority) return b.priority - a.priority;
      }
      const ta = a.article.publication_date ? new Date(a.article.publication_date).getTime() : 0;
      const tb = b.article.publication_date ? new Date(b.article.publication_date).getTime() : 0;
      return tb - ta;
    });
    return items;
  }, [withPriority, tickerFilter, priorityFilter, sortMode]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (loadError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">{loadError}</p>
        </CardContent>
      </Card>
    );
  }

  if (!state) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 pt-6 text-sm">
          <Loader2 className="size-4 animate-spin" />
          Starting first scan…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-xs">
        <span>Last updated: {timeAgo(news.last_success_at)}</span>
        {news.status === "error" && news.last_success_at && (
          <span className="text-amber-600 dark:text-amber-400">
            · Last refresh failed, showing previous results ({news.error_message})
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select value={tickerFilter} onValueChange={(v) => { setTickerFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="Stock" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All holdings</SelectItem>
            {tickers.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={priorityFilter} onValueChange={(v) => { setPriorityFilter(v as PriorityFilter); setPage(1); }}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Priority" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priority</SelectItem>
            <SelectItem value="high">Confirmed/candidate</SelectItem>
            <SelectItem value="low">General</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
          <SelectTrigger className="w-[150px]"><SelectValue placeholder="Sort" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="priority">Priority first</SelectItem>
            <SelectItem value="newest">Newest first</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Newspaper className="size-4" />
            News & Geopolitical Intelligence
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {anyScanning && (
            <div className="text-muted-foreground flex items-center gap-2 text-xs">
              <Loader2 className="size-3.5 animate-spin" />
              Scanning for updates…
            </div>
          )}
          {filtered.length === 0 && news.status !== "scanning" && (
            <p className="text-muted-foreground text-sm">No articles match this filter yet.</p>
          )}
          <div className="flex flex-col">
            {pageItems.map(({ article, priority }, i) => (
              <div
                key={`${article.url ?? article.title}-${i}`}
                className="border-border flex flex-col gap-1 border-b py-3 last:border-0 last:pb-0"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {article.ticker && <Badge variant="secondary">{article.ticker}</Badge>}
                  <Badge variant="outline" className="text-xs">{categoryFor(article, priority)}</Badge>
                  {publisherFromUrl(article.url) && (
                    <Badge variant="outline" className="text-xs">{publisherFromUrl(article.url)}</Badge>
                  )}
                  {looksNonEnglish(article.title) && (
                    <Badge variant="outline" className="text-xs text-amber-600 dark:text-amber-400">
                      Non-English source — not translated
                    </Badge>
                  )}
                  {article.publication_date && (
                    <span className="text-muted-foreground text-xs">
                      {new Date(article.publication_date).toLocaleDateString()}
                    </span>
                  )}
                  {article.url ? (
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-sm font-medium hover:underline"
                    >
                      {article.title}
                      <ExternalLink className="size-3.5" />
                    </a>
                  ) : (
                    <span className="text-sm font-medium">{article.title}</span>
                  )}
                </div>
                {article.summary && <p className="text-muted-foreground text-sm">{article.summary}</p>}
                <Button size="sm" variant="outline" className="mt-1 w-fit" onClick={() => onInvestigate(article)}>
                  Investigate Impact
                </Button>
              </div>
            ))}
          </div>

          {pageCount > 1 && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className={page === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="text-muted-foreground px-2 text-sm">
                    Page {page} of {pageCount}
                  </span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                    className={page === pageCount ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
