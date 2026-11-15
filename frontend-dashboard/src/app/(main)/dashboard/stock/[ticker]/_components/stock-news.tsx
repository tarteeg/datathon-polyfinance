import { ItemDescription } from "@/components/ui/item";
import type { Article } from "./article-dialog";
import { NewsArticleList } from "./news-article-list";

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
      [...new Set(symbols.flatMap((s) => [s, s.replaceAll(".", "-"), s.replace("-", ".")]))].join(","),
    );
  url.searchParams.set("limit", hours ? "500" : "50");
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

  return <NewsArticleList articles={stories} symbols={symbols} preferred={preferred} asOf={Date.now()} />;
}
