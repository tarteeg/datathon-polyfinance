import { formatDistanceToNowStrict } from "date-fns";
import { Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Item, ItemContent, ItemDescription, ItemGroup, ItemTitle } from "@/components/ui/item";

import { type Article, ArticleDialog } from "./article-dialog";

const sentimentStyles: Record<string, string> = {
  positive: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  neutral: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  negative: "bg-red-500/10 text-red-700 dark:text-red-400",
};

const normalizeTicker = (ticker: string) => ticker.trim().toUpperCase().replaceAll(".", "-");

export async function StockNews({
  symbols,
  hours,
  preferred = symbols,
}: {
  hours?: number;
  symbols?: string[];
  preferred?: string[];
}) {
  const url = new URL("/articles", process.env.BACKEND_API_URL || "http://127.0.0.1:8000");
  if (symbols?.length)
    url.searchParams.set(
      "tickers",
      [...new Set(symbols.flatMap((s) => [s, normalizeTicker(s), s.replace("-", ".")]))].join(","),
    );
  url.searchParams.set("limit", hours ? "500" : "10");
  if (hours) url.searchParams.set("hours", String(hours));

  let articles: Article[];
  try {
    const response = await fetch(url, { next: { revalidate: 60 }, signal: AbortSignal.timeout(30000) });
    if (!response.ok) throw new Error("Articles unavailable");
    articles = (await response.json()).articles;
  } catch {
    return <ItemDescription role="alert">Couldn’t load stock news.</ItemDescription>;
  }

  if (!articles.length) return <ItemDescription>No recent articles match this selection.</ItemDescription>;

  return (
    <ItemGroup className="gap-0 group-data-[view=cards]/news:grid group-data-[view=cards]/news:gap-3 md:group-data-[view=cards]/news:grid-cols-2 xl:group-data-[view=cards]/news:grid-cols-3">
      {Array.from(new Map(articles.map((article) => [article.url, article])).values()).map((article) => {
        const source = article.source || URL.parse(article.url)?.hostname.replace(/^www\./, "");

        const related = new Set(article.tickers?.map(normalizeTicker).filter(Boolean));
        const matched = preferred?.filter((s) => related.has(normalizeTicker(s))) ?? [];
        const shown = matched.length ? matched : symbols?.length === 1 ? symbols : [...related].slice(0, 1);
        for (const ticker of shown) related.delete(normalizeTicker(ticker));
        const published = Date.parse(article.publish_date ?? "");
        const sentiment = article.sentiment?.trim().toLowerCase();
        const score = article.importance_score;
        const impact = score == null ? null : score >= 0.8 ? "High" : score >= 0.5 ? "Medium" : "Low";
        const badges = (sentiment || impact) && (
          <div className="mt-1 flex flex-wrap gap-2">
            {sentiment && (
              <Badge variant="secondary" className={`capitalize ${sentimentStyles[sentiment] ?? ""}`}>
                <Info aria-hidden="true" />
                {sentiment}
              </Badge>
            )}
            {impact && (
              <Badge variant="secondary">
                <Info aria-hidden="true" />
                {impact} Impact
              </Badge>
            )}
          </div>
        );
        return (
          <Item
            key={article.url}
            role="listitem"
            className="group-data-[view=rows]/news:rounded-none group-data-[view=rows]/news:border-0 group-data-[view=rows]/news:border-b group-data-[view=rows]/news:border-border group-data-[view=rows]/news:px-0 group-data-[view=rows]/news:py-4 group-data-[view=rows]/news:last:border-b-0 group-data-[view=cards]/news:items-start group-data-[view=cards]/news:border-border group-data-[view=cards]/news:bg-card group-data-[view=cards]/news:p-4"
          >
            <ItemContent className="gap-2">
              <ItemDescription className="flex flex-wrap items-center gap-x-2 text-xs">
                {Number.isFinite(published) && (
                  <time dateTime={new Date(published).toISOString()} className="border-r pr-2">
                    {formatDistanceToNowStrict(published, { addSuffix: true })}
                  </time>
                )}
                {source && <span>{source} ·</span>}
                <span>
                  {shown.join(", ")}
                  {related.size > 0 && ` +${related.size}`}
                </span>
              </ItemDescription>
              <ItemTitle className="block line-clamp-none text-base font-semibold">
                <ArticleDialog article={article} source={source} badges={badges} />
              </ItemTitle>
              {badges}
            </ItemContent>
          </Item>
        );
      })}
    </ItemGroup>
  );
}
