import "server-only";
import type { ChartSnapshot } from "@/app/(main)/dashboard/chat/chart-snapshot";
import { requireSession } from "@/lib/session";
import { authPool } from "@/lib/db";

export async function modelReply(
  question: string,
  history: { question: string; answer: string }[],
  snapshot?: ChartSnapshot,
  previousNews?: unknown,
  previousStock?: unknown,
) {
  const { user } = await requireSession();
  const url = new URL("/chat", process.env.BACKEND_API_URL || "http://127.0.0.1:8000");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Chat-Key": process.env.CHAT_API_KEY ?? "" },
    body: JSON.stringify({
      persona: user.investorPersona,
      question,
      history,
      chart: snapshot?.facts,
      previous_news: previousNews,
      previous_stock: previousStock,
    }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Chat backend unavailable");
  const reply = await response.json();
  if (typeof reply.answer !== "string" || !reply.answer.trim()) throw new Error("Missing chat reply");
  return { answer: reply.answer as string, news: reply.news ?? null, stock: reply.stock ?? null };
}

export async function startChartChat(userId: string, snapshot: ChartSnapshot) {
  const threadId = crypto.randomUUID();
  const { symbol, period } = snapshot.facts;
  const question = `Explain the ${symbol} price chart (${period}).`;
  const { answer } = await modelReply(question, [], snapshot);
  await authPool.query(
    "INSERT INTO chat_turns (user_id, thread_id, turn, question, answer, chart_snapshot) VALUES ($1, $2, 1, $3, $4, $5)",
    [userId, threadId, question, answer, snapshot],
  );
  return threadId;
}
