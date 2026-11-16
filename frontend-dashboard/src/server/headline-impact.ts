"use server";

import { createHash } from "node:crypto";
import { revalidatePath } from "next/cache";

import { railHeadline } from "@/data/rail-headline";
import { sp500 } from "@/data/sp500";
import { authPool } from "@/lib/db";
import { requireSession } from "@/lib/session";
import { getHoldings } from "@/server/portfolio";

export type Headline = { title: string; url: string; published: string | null };
export type Replay = "august" | "november";
type Evidence = { ticker: string; text: string; url: string; published: string };
export type Impact = {
  direct: string[];
  watchlist?: string[];
  links: Evidence[];
  question: string | null;
  update: Evidence | null;
  connections: { ticker: string; explanation: string; quote: string; quote_source: "article" | "headline" | "feed_summary" | "issuer_note" | "results_note" }[];
  source_content_type: "full" | "excerpt" | "unknown" | "missing";
  title: string;
  published: string | null;
};

function threadId(owner: string, url: string, demo: boolean, persona?: string | null) {
  const key = createHash("sha256")
    .update(JSON.stringify(["headline", owner, url, demo, ...(persona ? [persona] : [])]))
    .digest("hex");
  return [key.slice(0, 8), key.slice(8, 12), "8" + key.slice(13, 16), "a" + key.slice(17, 20), key.slice(20, 32)].join(
    "-",
  );
}

const backend = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
const analysisVersion = 3; // Bump when the prompt or issuer evidence changes.

type FeedArticle = {
  title: string;
  url: string;
  publish_date?: string | null;
  authors?: string[] | null;
  source?: string | null;
  content?: string | null;
  source_content_type?: string | null;
  summary?: string | null;
  summary_short?: string | null;
  tickers?: string[] | null;
  primary_ticker?: string | null;
  entities?: string[] | null;
};

async function currentArticle(url: string) {
  const endpoint = new URL("/article", backend);
  endpoint.searchParams.set("url", url);
  const response = await fetch(endpoint, { cache: "no-store", signal: AbortSignal.timeout(25000) });
  if (!response.ok) throw new Error("Could not load the current article.");
  const { article }: { article: FeedArticle | null } = await response.json();
  if (!article?.title || article.url !== url) throw new Error("Article no longer available.");
  const content = article.content?.trim() ?? "";
  const label = article.source_content_type;
  return {
    title: article.title, url, published: article.publish_date?.slice(0, 10) || null,
    content, source_content_type: !content ? "missing" : label === "full" || label === "excerpt" ? label : "unknown",
    publish_date: article.publish_date ?? null, authors: article.authors ?? [],
    source: article.source ?? null, summary: article.summary || article.summary_short || null,
    tickers: (article.tickers ?? []).sort(), entities: (article.entities ?? []).sort(),
    primary_ticker: article.primary_ticker ?? null,
  };
}

async function lookup(owner: string, persona: string | null | undefined, url: string, replay?: Replay, includeChemtrade = true): Promise<Impact> {
  if (replay && url !== railHeadline.url) throw new Error("Unknown replay.");
  const [headline, holdings] = await Promise.all([
    replay ? { ...railHeadline, source_content_type: "missing" } : currentArticle(url),
    replay ? [] : getHoldings(),
  ]);
  const payload = JSON.stringify({
    headline, persona: persona || undefined, replay, include_chemtrade: replay ? includeChemtrade : undefined,
    holdings: holdings.map((h) => ({ ...h, name: sp500[h.ticker] ?? null })),
  });
  const key = threadId(owner, url, Boolean(replay), persona);
  const hash = createHash("sha256").update(String(analysisVersion)).update(payload).digest("hex");
  const db = await authPool.connect();
  try {
    await db.query("BEGIN");
    // Serialize simultaneous cache misses across dashboard instances.
    await db.query("SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [key]);
    const cached = await db.query<{ analysis: Impact }>(
      "SELECT analysis FROM headline_impact_cache WHERE user_id = $1 AND article_key = $2 AND input_hash = $3",
      [owner, key, hash],
    );
    let result = cached.rows[0]?.analysis;
    if (!result) {
      const response = await fetch(new URL("/headlines/impact", backend), {
        method: "POST", headers: { "Content-Type": "application/json", "X-Chat-Key": process.env.CHAT_API_KEY ?? "" },
        body: payload, cache: "no-store", signal: AbortSignal.timeout(60000),
      });
      if (!response.ok) throw new Error("Could not analyze the headline.");
      result = { ...await response.json(), title: headline.title, published: headline.published } as Impact;
      await db.query(
        `INSERT INTO headline_impact_cache (user_id, article_key, input_hash, analysis) VALUES ($1, $2, $3, $4)
         ON CONFLICT (user_id, article_key) DO UPDATE SET input_hash = EXCLUDED.input_hash, analysis = EXCLUDED.analysis`,
        [owner, key, hash, result],
      );
    }
    await db.query("COMMIT");
    return result;
  } catch (error) {
    await db.query("ROLLBACK");
    throw error;
  } finally {
    db.release();
  }
}

export async function checkHeadline(url: string, replay?: Replay, includeChemtrade = true) {
  const { user } = await requireSession();
  const id = threadId(user.id, url, Boolean(replay), user.investorPersona);
  const [result, saved] = await Promise.all([
    lookup(user.id, user.investorPersona, url, replay, includeChemtrade),
    authPool.query("SELECT 1 FROM chat_turns WHERE user_id = $1 AND thread_id = $2 AND turn = 1", [user.id, id]),
  ]);
  return { result, saved: saved.rowCount ? id : null };
}

export async function followHeadline(url: string, replay?: Replay, includeChemtrade = true) {
  const { user } = await requireSession();
  const result = await lookup(user.id, user.investorPersona, url, replay, includeChemtrade);
  if (!result.question) throw new Error("No supported connection to follow.");
  const id = threadId(user.id, url, Boolean(replay), user.investorPersona);
  const evidence = [...result.links, ...(result.update ? [result.update] : [])];
  const details = [
    replay ? "Historical replay · fictional CA$50,000 portfolio." : "Your portfolio when you followed this story.",
    result.direct.length ? "StocksFeed tagged these held companies: " + result.direct.join(", ") : "",
    result.watchlist?.length ? "Tagged companies you track without a share count: " + result.watchlist.join(", ") : "",
    ...result.connections.map((item) => item.ticker + ": " + item.explanation + '\n“' + item.quote + '”'),
    "Article coverage: " + result.source_content_type,
    ...evidence.map((item) => item.text),
    "Question to follow: " + result.question,
  ]
    .filter(Boolean)
    .join("\n\n");
  const stories = [
    { title: result.title, url, published: result.published },
    ...evidence.map((item) => ({
      title: item.ticker + " issuer disclosure",
      url: item.url,
      published: item.published,
    })),
  ];
  const sources = stories.map((s) => `[${s.published ?? "Undated"} · source](<${s.url}>)`).join("\n");
  await authPool.query(
    `INSERT INTO chat_turns (user_id, thread_id, turn, question, answer, news_snapshot)
     VALUES ($1, $2, 1, $3, $4, $5) ON CONFLICT (user_id, thread_id, turn) DO NOTHING`,
    [user.id, id, "Follow: " + result.title, details + "\n\n" + sources, { stories }],
  );
  revalidatePath("/dashboard/chat");
  return id;
}
