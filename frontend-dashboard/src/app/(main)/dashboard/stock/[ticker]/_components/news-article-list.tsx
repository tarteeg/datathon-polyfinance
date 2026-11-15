"use client";

import { formatDistanceStrict } from "date-fns";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Badge } from "@/components/ui/badge";
import { Item, ItemContent, ItemGroup, ItemTitle } from "@/components/ui/item";

import { type Article, ArticleDialog } from "./article-dialog";
import { ArticleThumbnail } from "./article-thumbnail";

import { HeadlineImpact } from "./headline-impact";

const sentimentStyles: Record<string, string> = {
  positive: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  neutral: "text-muted-foreground",
  negative: "bg-red-500/10 text-red-700 dark:text-red-400",
};

const normalizeTicker = (ticker: string) => ticker.trim().toUpperCase().replaceAll(".", "-");

const pageSize = 15;

function publisher(article: Article) {
  return article.source?.trim() || URL.parse(article.url)?.hostname.replace(/^www\./, "") || "Unknown source";
}

export function NewsArticleList({
  articles,
  symbols,
  preferred,
  asOf,
}: {
  articles: Article[];
  symbols?: string[];
  preferred?: string[];
  asOf: number;
}) {
  const [sourceFilter, setSourceFilter] = useState("");
  const [limit, setLimit] = useState(pageSize);
  const sources = [...new Set(articles.map(publisher))].sort((a, b) => a.localeCompare(b));
  const selected = sources.includes(sourceFilter) ? sourceFilter : "";
  const filtered = selected ? articles.filter((article) => publisher(article) === selected) : articles;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex min-w-0 items-center gap-2 text-sm">
          Source
          <NativeSelect
            aria-label="News source"
            value={selected}
            onChange={(event) => {
              setSourceFilter(event.target.value);
              setLimit(pageSize);
            }}
          >
            <NativeSelectOption value="">All sources</NativeSelectOption>
            {sources.map((source) => (
              <NativeSelectOption key={source} value={source}>
                {source}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </label>
        <span role="status" className="text-xs text-muted-foreground">
          {Math.min(limit, filtered.length)} of {filtered.length} {filtered.length === 1 ? "article" : "articles"}
        </span>
      </div>
      <ItemGroup className="gap-0 group-data-[view=cards]/news:grid group-data-[view=cards]/news:gap-4 @xl:group-data-[view=cards]/news:grid-cols-2 @4xl:group-data-[view=cards]/news:grid-cols-3">
        {filtered.slice(0, limit).map((article) => {
          const source = publisher(article);

          const related = new Set(article.tickers?.map(normalizeTicker).filter(Boolean));
          const matched = preferred?.filter((s) => related.has(normalizeTicker(s))) ?? [];
          const shown = matched.length ? matched : symbols?.length === 1 ? symbols : [...related].slice(0, 1);
          for (const ticker of shown) related.delete(normalizeTicker(ticker));
          const published = Date.parse(article.publish_date ?? "");
          const sentiment = article.sentiment?.trim().toLowerCase();
          const score = article.importance_score;
          const impact = score == null ? null : score >= 0.8 ? "High" : score >= 0.5 ? "Medium" : "Low";
          const summary = article.summary_short?.trim() || article.summary?.trim();
          const badges = (sentiment || impact) && (
            <div className="flex flex-wrap items-center gap-1.5">
              {sentiment && (
                <Badge variant="secondary" className={`capitalize ${sentimentStyles[sentiment] ?? ""}`}>
                  {sentiment}
                </Badge>
              )}
              {impact && <Badge variant="secondary">{impact} impact</Badge>}
            </div>
          );
          return (
            <Item
              key={article.url}
              role="listitem"
              className="min-w-0 flex-nowrap gap-4 group-data-[view=rows]/news:rounded-none group-data-[view=rows]/news:border-0 group-data-[view=rows]/news:border-b group-data-[view=rows]/news:border-border group-data-[view=rows]/news:px-0 group-data-[view=rows]/news:py-5 group-data-[view=cards]/news:flex-col group-data-[view=cards]/news:items-stretch group-data-[view=cards]/news:gap-0 group-data-[view=cards]/news:overflow-hidden group-data-[view=cards]/news:rounded-xl group-data-[view=cards]/news:border-border group-data-[view=cards]/news:bg-card group-data-[view=cards]/news:p-0 @4xl:group-data-[view=cards]/news:first:col-span-2 @4xl:group-data-[view=cards]/news:first:bg-muted/30"
            >
              {article.image_url && <ArticleThumbnail key={article.image_url} src={article.image_url} />}
              <ItemContent className="min-w-0 gap-2 group-data-[view=cards]/news:p-5">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  {shown.length > 0 && (
                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono font-semibold text-foreground">
                      {shown.join(", ")}
                      {related.size > 0 && ` +${related.size}`}
                    </span>
                  )}
                  {source && <span className="font-medium">{source}</span>}
                  {Number.isFinite(published) && (
                    <time dateTime={new Date(published).toISOString()}>
                      {formatDistanceStrict(published, asOf, { addSuffix: true })}
                    </time>
                  )}
                </div>
                <ItemTitle className="block w-full line-clamp-none text-lg leading-snug font-semibold tracking-tight @4xl:group-data-[view=cards]/news:group-first/item:text-2xl">
                  <ArticleDialog article={article} source={source} badges={badges} />
                </ItemTitle>
                {summary && summary !== article.title && (
                  <p className="hidden text-sm leading-relaxed text-muted-foreground group-data-[view=cards]/news:line-clamp-2">
                    {summary}
                  </p>
                )}
                <div className="mt-auto flex flex-wrap items-center justify-between gap-x-2 gap-y-1 pt-2 group-data-[view=cards]/news:border-t group-data-[view=cards]/news:border-border/60">
                  {badges}
                  {["https:", "http:"].includes(URL.parse(article.url)?.protocol ?? "") && (
                    <HeadlineImpact
                      headline={{
                        title: article.title,
                        url: article.url,
                        published: Number.isFinite(published) ? new Date(published).toISOString().slice(0, 10) : null,
                      }}
                    />
                  )}
                </div>
              </ItemContent>
            </Item>
          );
        })}
      </ItemGroup>
      {limit < filtered.length && (
        <Button variant="outline" className="self-center" onClick={() => setLimit(limit + pageSize)}>
          Show more articles
        </Button>
      )}
    </div>
  );
}
