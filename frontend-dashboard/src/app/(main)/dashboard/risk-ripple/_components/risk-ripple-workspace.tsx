"use client";

import { ChevronDown, ExternalLink, Loader2, Newspaper, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { pollAlertsScan, triggerAlertsScan, type CombinedScanState } from "@/server/alerts-actions";
import type { AlertMatch, NewsArticle, ScanResponse } from "@/server/riskripple";

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
    case 1:
      return "Article discovered";
    case 2:
      return "Event reported";
    case 3:
      return "Materially significant";
    case 4:
      return "Potential portfolio exposure";
    case 5:
      return "Evidence-supported exposure";
    default:
      return "Candidate";
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
            <Badge variant="outline" className="text-xs">
              {tierLabel(match.classification_tier)}
            </Badge>
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
            &quot;{match.evidence_snippet}&quot;
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

function AlertsSection({ combined, scanning }: { combined: { confirmed: AlertMatch[]; candidates: AlertMatch[] }; scanning: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="size-4" />
          Portfolio Alerts &amp; Investigations
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {scanning && (
          <div className="text-muted-foreground flex items-center gap-2 text-xs">
            <Loader2 className="size-3.5 animate-spin" />
            Scanning for updates…
          </div>
        )}

        <div>
          <h3 className="mb-1 text-sm font-medium">Confirmed alerts</h3>
          {combined.confirmed.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No confirmed alerts right now — checked real Federal Register documents and real recent news against
              your actual holdings.
            </p>
          ) : (
            <Accordion type="multiple">
              {combined.confirmed.map((m, i) => (
                <MatchAccordionItem key={`confirmed-${i}`} match={m} keyId={`confirmed-${i}`} />
              ))}
            </Accordion>
          )}
        </div>

        {combined.candidates.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-xs hover:underline">
              <ChevronDown className="size-3.5" />
              {combined.candidates.length} investigation candidate{combined.candidates.length === 1 ? "" : "s"} (plausible,
              not yet confirmed)
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              <Accordion type="multiple">
                {combined.candidates.map((m, i) => (
                  <MatchAccordionItem key={`candidate-${i}`} match={m} keyId={`candidate-${i}`} />
                ))}
              </Accordion>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

export function RiskRippleWorkspace({ defaultTickers }: { defaultTickers: string }) {
  const [state, setState] = useState<CombinedScanState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [prefill, setPrefill] = useState<Prefill | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const formRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef(false);

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
        // A failed poll is silently ignored -- keep showing the last good state and
        // retry next tick, per the backend's own disclosed polling-under-load flakiness.
        if (result.ok) {
          setState((prev) => (prev ? { ...prev, news: result.data.news, regulatory: result.data.regulatory } : prev));
        }
      } finally {
        pollingRef.current = false;
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [state?.news.status, state?.regulatory.status]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleInvestigateImpact(article: NewsArticle) {
    setPrefill({ eventDescription: `${article.title}. ${article.summary}`.trim(), tickers: article.ticker ?? "" });
    setFormOpen(true);
    requestAnimationFrame(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
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
  const anyErrorNoData =
    (news.status === "error" && !news.last_success_at) || (regulatory.status === "error" && !regulatory.last_success_at);

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

      {anyErrorNoData && !state && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive text-sm">
              {news.error_message || regulatory.error_message || "Scan failed and no previous results are available."}
            </p>
          </CardContent>
        </Card>
      )}

      {!state && !loadError && (
        <Card>
          <CardContent className="flex items-center gap-2 pt-6 text-sm">
            <Loader2 className="size-4 animate-spin" />
            Starting first scan…
          </CardContent>
        </Card>
      )}

      {state && (
        <>
          <NewsSectionWithAction news={news} regulatoryScanning={anyScanning} onInvestigate={handleInvestigateImpact} />
          <AlertsSection combined={{ confirmed, candidates }} scanning={anyScanning} />
        </>
      )}

      <div ref={formRef}>
        <Collapsible open={formOpen} onOpenChange={setFormOpen}>
          <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-sm hover:underline">
            <ChevronDown className="size-4" />
            Ask about a specific event instead
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <InvestigateForm defaultTickers={defaultTickers} prefill={prefill} />
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}

function NewsSectionWithAction({
  news,
  regulatoryScanning,
  onInvestigate,
}: {
  news: ScanResponse;
  regulatoryScanning: boolean;
  onInvestigate: (article: NewsArticle) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Newspaper className="size-4" />
          News &amp; Geopolitical Intelligence
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {(news.status === "scanning" || regulatoryScanning) && (
          <div className="text-muted-foreground flex items-center gap-2 text-xs">
            <Loader2 className="size-3.5 animate-spin" />
            Scanning for updates…
          </div>
        )}
        {news.articles.length === 0 && news.status !== "scanning" && (
          <p className="text-muted-foreground text-sm">No recent articles found for your holdings yet.</p>
        )}
        <div className="flex flex-col">
          {news.articles.map((article, i) => (
            <div
              key={`${article.url ?? article.title}-${i}`}
              className="border-border flex flex-col gap-1 border-b py-3 last:border-0 last:pb-0"
            >
              <div className="flex flex-wrap items-center gap-2">
                {article.ticker && <Badge variant="secondary">{article.ticker}</Badge>}
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
      </CardContent>
    </Card>
  );
}
