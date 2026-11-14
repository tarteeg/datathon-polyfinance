import type { ReactNode } from "react";
import { RelatedStock } from "./related-stock";
import { ArrowUpRight, ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export type Article = {
  authors?: string[] | null;
  tickers?: string[] | null;
  summary_short?: string | null;
  summary?: string | null;
  summary_bullets?: string[] | null;
  sentiment_reasoning?: string | null;
  importance_reasoning?: string | null;
  url: string;
  title: string;
  source?: string | null;
  sentiment?: string | null;
  importance_score?: number | null;
  publish_date?: string | null;
};

const publicationDate = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

export function ArticleDialog({ article, source, badges }: { article: Article; source?: string; badges: ReactNode }) {
  const published = Date.parse(article.publish_date ?? "");
  const summary = article.summary_short?.trim() || article.summary?.trim();
  const normalize = (text: string) =>
    text
      .toLowerCase()
      .replace(/[.,!?;:"“”‘’()[\]—–-]+/g, " ").replace(/\s+/g, " ")
      .trim();
  const seen = new Set([normalize(article.title), normalize(summary ?? "")]);
  const bullets = (article.summary_bullets ?? [])
    .filter((bullet) => {
      const key = normalize(bullet);
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 3);
  const tickers = [...new Set(article.tickers?.filter(Boolean))];
  const original = URL.parse(article.url);
  const reasons = [
    ["Sentiment", article.sentiment && article.sentiment_reasoning],
    ["Impact", article.importance_score != null && article.importance_reasoning],
  ].filter(([, reason]) => reason);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className="cursor-pointer rounded-sm text-left hover:underline focus-visible:outline-ring"
        >
          {article.title}
        </button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
        <div className="min-h-0 overflow-y-auto p-5 sm:p-6">
          <DialogHeader className="pr-8">
            <DialogTitle className="text-xl leading-snug sm:text-2xl">{article.title}</DialogTitle>
            <DialogDescription>
              {[
                source,
                Number.isFinite(published) && publicationDate.format(published) + " UTC",
                article.authors?.length && `By ${article.authors.join(", ")}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </DialogDescription>
          </DialogHeader>
          {(summary || bullets.length > 0) && (
            <section className="mt-6 flex flex-col gap-2">
              <h3 className="text-sm font-medium text-muted-foreground">Summary</h3>
              {summary && <p className="leading-relaxed">{summary}</p>}
              {bullets.length > 0 && (
                <ul className="flex list-disc flex-col gap-1 pl-5">
                  {bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              )}
            </section>
          )}
          {badges && <div className="mt-4">{badges}</div>}
          {reasons.length > 0 && (
            <Collapsible className="mt-2">
              <CollapsibleTrigger asChild>
                <Button size="sm" variant="ghost" className="group px-0">
                  Why these labels?
                  <ChevronDown className="group-data-[state=open]:rotate-180" />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="flex flex-col gap-2 text-sm leading-relaxed">
                {reasons.map(([label, reason]) => (
                  <p key={String(label)}>
                    <strong>{label}.</strong> {reason}
                  </p>
                ))}
              </CollapsibleContent>
            </Collapsible>
          )}
          {tickers.length > 0 && (
            <nav aria-label="Related stocks" className="mt-5 flex flex-wrap gap-2 text-sm">
              {tickers.map((ticker) => (
                <RelatedStock key={ticker} ticker={ticker} />
              ))}
            </nav>
          )}
        </div>
        {original && ["http:", "https:"].includes(original.protocol) && (
          <DialogFooter className="m-0 shrink-0">
            <Button asChild>
              <a href={original.href} target="_blank" rel="noopener noreferrer">
                Read original{source && ` on ${source}`} <ArrowUpRight />
              </a>
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
