"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getHistory } from "@/server/alerts-actions";
import type { InvestigationHistoryEntry } from "@/server/riskripple";

import { ATTENTION_META } from "./findings-cards";
import { HistoryEntryItem } from "./history-entry-item";

type AttentionFilter = "all" | keyof typeof ATTENTION_META;

const HISTORY_LIMIT = 50;

export function HistoryWorkspace() {
  const [history, setHistory] = useState<InvestigationHistoryEntry[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tickerFilter, setTickerFilter] = useState<string>("all");
  const [attentionFilter, setAttentionFilter] = useState<AttentionFilter>("all");

  useEffect(() => {
    let cancelled = false;
    getHistory(HISTORY_LIMIT).then((result) => {
      if (cancelled) return;
      if (result.ok) setHistory(result.data);
      else setLoadError("Couldn't load past investigations. Try reloading the page.");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">{loadError}</p>
        </CardContent>
      </Card>
    );
  }

  if (history === null) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 pt-6 text-sm">
          <Loader2 className="size-4 animate-spin" />
          Loading past investigations…
        </CardContent>
      </Card>
    );
  }

  const tickerSet = new Set<string>();
  for (const h of history) for (const t of h.portfolio_holdings) tickerSet.add(t);
  const tickers = [...tickerSet].sort();

  const filtered = history.filter((h) => {
    if (tickerFilter !== "all" && !h.portfolio_holdings.includes(tickerFilter)) return false;
    if (attentionFilter !== "all" && h.result.event_briefing?.attention_level !== attentionFilter) return false;
    return true;
  });

  function handleDeleted(id: number) {
    setHistory((prev) => prev && prev.filter((h) => h.id !== id));
  }

  return (
    <div className="flex flex-col gap-4">
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
        <Select value={attentionFilter} onValueChange={(v) => setAttentionFilter(v as AttentionFilter)}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Verdict" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All verdicts</SelectItem>
            {Object.entries(ATTENTION_META).map(([key, meta]) => (
              <SelectItem key={key} value={key}>{meta.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          {filtered.length === 0 ? (
            <p className="text-muted-foreground text-sm">No past manual investigations for this filter.</p>
          ) : (
            filtered.map((h, i) => (
              <HistoryEntryItem key={h.id} entry={h} defaultOpen={i === 0} onDeleted={handleDeleted} />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
