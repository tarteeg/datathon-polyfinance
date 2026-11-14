import { z } from "zod";

import type { ChartSnapshot } from "@/app/(main)/dashboard/chat/chart-snapshot";
import type { ChatTurn } from "@/app/(main)/dashboard/chat/actions";
import { type ChatActivity, readChatStream, savedChatAnswer } from "@/lib/chat-stream";
import { authPool } from "@/lib/db";
import { getHoldings } from "@/server/portfolio";
import { getSession } from "@/lib/session";

const payload = z.object({
  threadId: z.uuid(),
  question: z.string().trim().min(1).max(4000),
  lastTurn: z.number().int().nonnegative(),
});

export async function POST(request: Request) {
  const session = await getSession();
  if (!session) return new Response("Sign in to chat.", { status: 401 });
  const { user } = session;
  const parsed = payload.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return new Response("Invalid chat message.", { status: 400 });
  const { question, threadId, lastTurn } = parsed.data;
  const recent = await authPool.query<ChatTurn>(
    "SELECT turn, question, answer FROM chat_turns WHERE user_id = $1 AND thread_id = $2 ORDER BY turn DESC LIMIT 10",
    [user.id, threadId],
  );
  const latest = recent.rows[0]?.turn ?? 0;
  const conflict = "Your chat changed in another request. Reload the conversation.";
  if (lastTurn !== latest) return new Response(conflict, { status: 409 });

  const first = await authPool.query<{ chart_snapshot: ChartSnapshot | null }>(
    "SELECT chart_snapshot FROM chat_turns WHERE user_id = $1 AND thread_id = $2 AND turn = 1",
    [user.id, threadId],
  );
  const snapshot = first.rows[0]?.chart_snapshot;
  const previous = await authPool.query(
    "SELECT news_snapshot FROM chat_turns WHERE user_id = $1 AND thread_id = $2 AND news_snapshot IS NOT NULL ORDER BY turn DESC LIMIT 1",
    [user.id, threadId],
  );
  const stock = await authPool.query(
    `SELECT CASE WHEN stock_snapshot ? 'stocks' THEN jsonb_build_object('stocks', (
       SELECT jsonb_agg(item - 'points' ORDER BY ord)
       FROM jsonb_array_elements(stock_snapshot->'stocks') WITH ORDINALITY AS entries(item, ord)
     )) ELSE stock_snapshot - 'points' END AS stock_snapshot
     FROM chat_turns WHERE user_id = $1 AND thread_id = $2 AND stock_snapshot IS NOT NULL
     ORDER BY turn DESC LIMIT 1`,
    [user.id, threadId],
  );
  const upstream = await fetch(new URL("/chat/stream", process.env.BACKEND_API_URL || "http://127.0.0.1:8000"), {
    method: "POST",
    signal: request.signal,
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-Chat-Key": process.env.CHAT_API_KEY ?? "" },
    body: JSON.stringify({
      question,
      holdings: await getHoldings(),
      history: recent.rows.reverse().map(({ question, answer }) => ({ question, answer: savedChatAnswer(answer) })),
      chart: snapshot?.facts,
      previous_news: previous.rows[0]?.news_snapshot,
      previous_stock: stock.rows[0]?.stock_snapshot,
    }),
  }).catch(() => null);
  if (!upstream?.ok) return new Response("The assistant is unavailable.", { status: 502 });

  const encoder = new TextEncoder();
  const body = new ReadableStream({
    async start(controller) {
      const send = (event: unknown) => controller.enqueue(encoder.encode(JSON.stringify(event) + "\n"));
      let answer = "";
      const activity = new Map<string, ChatActivity>();
      try {
        for await (const event of readChatStream(upstream)) {
          if (request.signal.aborted) return;
          if (event.activity) {
            activity.set(event.activity.id, event.activity);
            send({ activity: event.activity });
            continue;
          }
          if (typeof event.delta === "string") {
            answer += event.delta;
            send({ delta: event.delta });
            continue;
          }
          if (event.done && answer.trim()) {
            const saved = await authPool.query(
              `INSERT INTO chat_turns (user_id, thread_id, turn, question, answer, news_snapshot, stock_snapshot, portfolio_snapshot, tool_activity)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (user_id, thread_id, turn) DO NOTHING`,
              [
                user.id,
                threadId,
                latest + 1,
                question,
                answer,
                event.news,
                event.stock,
                event.portfolio,
                JSON.stringify([...activity.values()]),
              ],
            );
            send(saved.rowCount ? { done: true, stock: event.stock, portfolio: event.portfolio } : { error: conflict });
            return;
          }
          break;
        }
        send({ error: "The reply was interrupted. Reload the conversation to retry." });
      } catch {
        if (!request.signal.aborted)
          send({ error: "Could not confirm delivery. Reload the conversation before retrying." });
      } finally {
        if (!request.signal.aborted) controller.close();
      }
    },
  });
  return new Response(body, {
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-store, no-transform",
      "X-Accel-Buffering": "no",
      "X-Message-Id": `${threadId}-${latest + 1}`,
    },
  });
}
