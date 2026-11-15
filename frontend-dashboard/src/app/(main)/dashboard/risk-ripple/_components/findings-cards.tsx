"use client";

import { ArrowDownRight, ChevronDown, ExternalLink, Wrench } from "lucide-react";
import { useMemo, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock, CodeBlockContent } from "@/components/ui/code-block";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableCell, TableHead } from "@/components/ui/table";
import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import type { InvestigateResult } from "@/server/riskripple";

// Matches the finance-chat / investigate-form markdown pattern for visual consistency.
function AnswerMarkdown({ text }: { text: string }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      disallowedElements={["img"]}
      components={{
        table: ({ children }) => <Table>{children}</Table>,
        td: ({ children }) => <TableCell className="whitespace-normal">{children}</TableCell>,
        th: ({ children }) => (
          <TableHead scope="col" className="whitespace-normal">
            {children}
          </TableHead>
        ),
      }}
    >
      {text}
    </Markdown>
  );
}

// Tier vocabulary matches TIER_SHOCKS exactly (backend-server/app/riskripple/finance/stress.py) --
// priority and confidence are deliberately SEPARATE fields, not merged into one label.
const TIER_META: Record<string, { priority: "High" | "Medium" | "Low" | "None"; priorityRank: number; confidence: string }> = {
  direct_verified: { priority: "High", priorityRank: 3, confidence: "Verified" },
  indirect_evidence_supported: { priority: "Medium", priorityRank: 2, confidence: "Evidence-supported" },
  unverified_possibility: { priority: "Low", priorityRank: 1, confidence: "Unverified" },
  no_established_link: { priority: "None", priorityRank: 0, confidence: "No link found" },
};
const UNKNOWN_TIER_META = { priority: "Unknown" as const, priorityRank: -1, confidence: "Not yet investigated" };

function tierMeta(tier: string | undefined) {
  return (tier && TIER_META[tier]) || UNKNOWN_TIER_META;
}

function priorityBadgeVariant(priority: string): "default" | "secondary" | "outline" {
  if (priority === "High") return "default";
  if (priority === "Medium" || priority === "Low") return "secondary";
  return "outline";
}

function formatMoney(n: number | undefined): string {
  if (n == null || Number.isNaN(n)) return "Not quantified";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 })}`;
}

function formatPct(n: number | undefined): string {
  if (n == null || Number.isNaN(n)) return "";
  return `${(n * 100).toFixed(1)}%`;
}

// Deterministic next-step generation -- no LLM call, only derived from fields the
// card already shows elsewhere on the page. Research/monitoring actions only, never
// buy/sell language, per the house tone established everywhere else in this app.
function nextSteps(args: {
  tier: string | undefined;
  hasQuantifiedImpact: boolean;
  followup: InvestigateResult["followup_investigation"];
}): string[] {
  const steps: string[] = [];
  const { tier, hasQuantifiedImpact, followup } = args;

  if (followup && followup.classification !== "supported") {
    steps.push(`Investigate further: "${followup.question}" — currently ${followup.classification}.`);
  }
  if (tier === "no_established_link") {
    steps.push("No evidence-based reason to change this position has been established from the sources checked.");
  } else if (tier === "unverified_possibility" || !tier) {
    steps.push("Review subsequent company disclosures or regulatory filings before treating this as a material portfolio risk.");
  }
  if (hasQuantifiedImpact) {
    steps.push("Review the quantified scenario impact below before drawing conclusions.");
  }
  if (steps.length === 0) {
    steps.push("Monitor for further disclosures or regulatory updates on this topic.");
  }
  return steps.slice(0, 3);
}

// Small, curated extraction of real source URLs already present in the agent's own
// tool-call trace -- never fabricated; omitted entirely if none are found for real.
function extractSources(trace: InvestigateResult["trace"]): { url: string; label: string }[] {
  const seen = new Map<string, string>();
  for (const message of trace) {
    for (const block of message.content) {
      if (block.type !== "tool_result") continue;
      const raw = typeof block.content === "string" ? block.content : JSON.stringify(block.content);
      const matches = raw.matchAll(/"(?:document_url|source_url)"\s*:\s*"([^"]+)"/g);
      for (const m of matches) {
        const url = m[1];
        if (url && !seen.has(url)) {
          let label = url;
          try {
            label = new URL(url).hostname.replace(/^www\./, "");
          } catch {
            /* keep raw url as label */
          }
          seen.set(url, label);
        }
      }
    }
  }
  return Array.from(seen, ([url, label]) => ({ url, label }));
}

type SortMode = "priority" | "recency" | "ticker";

export function FindingsCards({ result }: { result: InvestigateResult }) {
  const [tickerFilter, setTickerFilter] = useState<string>("all");
  const [sortMode, setSortMode] = useState<SortMode>("priority");

  const classifications = result.exposure_classifications ?? {};
  const portfolioImpact = result.portfolio_impact;
  const hasRealImpact = !!portfolioImpact && !portfolioImpact.error;
  const sources = useMemo(() => extractSources(result.trace), [result.trace]);
  const followup = result.followup_investigation;

  const findings = useMemo(() => {
    return result.portfolio_holdings.map((symbol) => {
      const entry = classifications[symbol];
      const meta = tierMeta(entry?.tier);
      const positionPnl = portfolioImpact?.scenario_position_pnl?.[symbol];
      const hasQuantifiedImpact = hasRealImpact && positionPnl != null;
      return {
        symbol,
        tier: entry?.tier,
        meta,
        reason: entry?.reason || "Not yet investigated by the agent for this event.",
        hasQuantifiedImpact,
        positionPnl,
        steps: nextSteps({ tier: entry?.tier, hasQuantifiedImpact, followup }),
      };
    });
  }, [result.portfolio_holdings, classifications, portfolioImpact, hasRealImpact, followup]);

  const filtered = tickerFilter === "all" ? findings : findings.filter((f) => f.symbol === tickerFilter);
  const sorted = [...filtered].sort((a, b) => {
    if (sortMode === "priority") return b.meta.priorityRank - a.meta.priorityRank;
    if (sortMode === "ticker") return a.symbol.localeCompare(b.symbol);
    return 0; // "recency" -- a single investigation shares one timestamp, so this falls back to input order.
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-xs">Filter by stock</span>
          <Select value={tickerFilter} onValueChange={setTickerFilter}>
            <SelectTrigger className="h-8 w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All holdings</SelectItem>
              {result.portfolio_holdings.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-xs">Sort by</span>
          <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
            <SelectTrigger className="h-8 w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="priority">Highest priority</SelectItem>
              <SelectItem value="recency">Most recent</SelectItem>
              <SelectItem value="ticker">Ticker</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Badge variant="outline" className="ml-auto text-xs">
          {sorted.length} finding{sorted.length === 1 ? "" : "s"}
        </Badge>
      </div>

      {sorted.length === 0 && (
        <p className="text-muted-foreground text-sm">
          No findings yet for {tickerFilter === "all" ? "this event" : tickerFilter} — this does not mean no exposure
          exists, only that none has been investigated or confirmed.
        </p>
      )}

      {sorted.map((f) => (
        <Card key={f.symbol}>
          <CardContent className="flex flex-col gap-3 pt-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{f.symbol}</Badge>
              <Badge variant={priorityBadgeVariant(f.meta.priority)} className="text-xs">
                {f.meta.priority === "None" ? "No established link" : `${f.meta.priority} priority`}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {f.meta.confidence}
              </Badge>
              <span className="text-muted-foreground ml-auto text-xs">
                {f.hasQuantifiedImpact ? formatMoney(f.positionPnl) : "Impact not quantified"}
              </span>
            </div>

            <p className="text-sm font-medium">{result.event_description}</p>
            <p className="text-muted-foreground text-sm">{f.reason}</p>

            <div>
              <h4 className="mb-1 text-xs font-medium">What this means for you</h4>
              <ul className="text-muted-foreground flex flex-col gap-1 text-sm">
                {f.steps.map((step, i) => (
                  <li key={i} className="flex gap-2">
                    <span aria-hidden>•</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Collapsible>
              <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-xs hover:underline">
                <ChevronDown className="size-3.5" />
                View evidence
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 flex flex-col gap-2">
                {sources.length > 0 ? (
                  <ul className="flex flex-col gap-1">
                    {sources.map((s) => (
                      <li key={s.url}>
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex w-fit items-center gap-1 text-sm hover:underline"
                        >
                          {s.label}
                          <ExternalLink className="size-3.5" />
                        </a>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    No external source links were captured in this run's tool trace.
                  </p>
                )}
              </CollapsibleContent>
            </Collapsible>
          </CardContent>
        </Card>
      ))}

      <Collapsible>
        <CollapsibleTrigger className="text-muted-foreground flex items-center gap-2 text-xs hover:underline">
          <Wrench className="size-3.5" />
          Investigation steps & full report ({result.trace.length} trace messages)
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 flex flex-col gap-4">
          {result.answer && (
            <div className="text-sm [&>*+*]:mt-2">
              <AnswerMarkdown text={result.answer} />
            </div>
          )}
          <Trace>
            {result.trace.flatMap((message, i) =>
              message.content.map((block, j) => {
                const key = `${i}-${j}`;
                if (block.type === "text") {
                  if (message.role !== "assistant") return null;
                  return (
                    <p key={key} className="text-muted-foreground text-sm">
                      {block.text}
                    </p>
                  );
                }
                if (block.type === "tool_use") {
                  return (
                    <TraceCollapsible key={key}>
                      <TraceCollapsibleTrigger>
                        <TraceLine>
                          <TraceIcon>
                            <Wrench />
                          </TraceIcon>
                          <TraceTitle>{block.name ?? "tool call"}</TraceTitle>
                        </TraceLine>
                      </TraceCollapsibleTrigger>
                      <TraceCollapsibleContent>
                        <CodeBlock size="sm">
                          <CodeBlockContent wrap>{JSON.stringify(block.input ?? {}, null, 2)}</CodeBlockContent>
                        </CodeBlock>
                      </TraceCollapsibleContent>
                    </TraceCollapsible>
                  );
                }
                if (block.type === "tool_result") {
                  const content =
                    typeof block.content === "string" ? block.content : JSON.stringify(block.content, null, 2);
                  return (
                    <TraceCollapsible key={key}>
                      <TraceCollapsibleTrigger>
                        <TraceLine status={block.status === "error" ? "error" : undefined}>
                          <TraceIcon>
                            <ArrowDownRight />
                          </TraceIcon>
                          <TraceTitle>result{block.status ? ` (${block.status})` : ""}</TraceTitle>
                        </TraceLine>
                      </TraceCollapsibleTrigger>
                      <TraceCollapsibleContent>
                        <CodeBlock size="sm">
                          <CodeBlockContent wrap>{content}</CodeBlockContent>
                        </CodeBlock>
                      </TraceCollapsibleContent>
                    </TraceCollapsible>
                  );
                }
                return null;
              }),
            )}
          </Trace>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
