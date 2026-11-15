import { ItemDescription } from "@/components/ui/item";
import type { Article } from "./article-dialog";
import { NewsArticleList } from "./news-article-list";

export async function StockNews({
  source,
  symbols,
  hours,
  preferred = symbols,
}: {
  source: string;
  hours?: number;
  symbols?: string[];
  preferred?: string[];
}) {
  const url = new URL("/articles", process.env.BACKEND_API_URL || "http://127.0.0.1:8000");
  if (symbols?.length)
    url.searchParams.set(
      "tickers",
      [...new Set(symbols.flatMap((s) => [s, s.replaceAll(".", "-"), s.replace("-", ".")]))].join(","),
    );
  url.searchParams.set("limit", hours ? "500" : "50");
  url.searchParams.set("include_sources", "true");
  if (source) url.searchParams.set("source", source);
  if (hours) url.searchParams.set("hours", String(hours));

  let articles: Article[];
  let sources: string[];
  try {
    const response = await fetch(url, { next: { revalidate: 60 }, signal: AbortSignal.timeout(30000) });
    if (!response.ok) throw new Error("Articles unavailable");
    const payload = await response.json();
    articles = payload.articles;
    sources = payload.sources ?? [];
  } catch {
    return <ItemDescription role="alert">Couldn’t load stock news.</ItemDescription>;
  }

  // The feed also returns article bodies and extraction metadata. Only send fields used by the list and dialogs.
  const stories = Array.from(new Map(articles.map((article) => [article.url, article])).values(), (article) => {
    const {
      url,
      title,
      image_url,
      publish_date,
      authors,
      source,
      tickers,
      summary,
      summary_short,
      summary_bullets,
      sentiment,
      sentiment_reasoning,
      importance_score,
      importance_reasoning,
    } = article;
    return {
      url,
      title,
      image_url,
      publish_date,
      authors,
      source,
      tickers,
      summary,
      summary_short,
      summary_bullets,
      sentiment,
      sentiment_reasoning,
      importance_score,
      importance_reasoning,
    };
  });

  return <NewsArticleList key={source} sourceFilter={source} sources={sources} articles={stories} symbols={symbols} preferred={preferred} asOf={Date.now()} />;
}
