"use server";

import type { ChartSnapshot } from "./chart-snapshot";
import { modelReply } from "@/server/chart-chat";
import { authPool } from "@/lib/db";
import { requireSession } from "@/lib/session";

export type ChatTurn = { turn: number; question: string; answer: string; chart_snapshot?: ChartSnapshot | null };

export async function listThreads() {
  const { user } = await requireSession();
  const { rows } = await authPool.query<{ id: string; title: string; createdAt: string; updatedAt: string }>(
    `SELECT first.thread_id AS id, left(first.question, 72) AS title, first.created_at::text AS "createdAt", activity.latest::text AS "updatedAt"
     FROM chat_turns first
     JOIN (SELECT thread_id, max(created_at) AS latest FROM chat_turns WHERE user_id = $1 GROUP BY thread_id) activity
       USING (thread_id)
     WHERE first.user_id = $1 AND first.turn = 1 ORDER BY activity.latest DESC, first.thread_id`,
    [user.id],
  );
  return { threads: rows };
}

export async function loadHistory(threadId: string) {
  const { user } = await requireSession();
  const history = await authPool.query<ChatTurn>(
    "SELECT turn, question, answer, chart_snapshot FROM chat_turns WHERE user_id = $1 AND thread_id = $2 ORDER BY turn",
    [user.id, threadId],
  );
  return history.rows;
}

export async function sendMessage(threadId: string, question: string, lastTurn: number) {
  const { user } = await requireSession();
  if (typeof question !== "string" || !question.trim() || question.length > 4000) {
    return { error: "Enter a message of up to 4,000 characters." } as const;
  }
  const recent = await authPool.query<ChatTurn>(
    "SELECT turn, question, answer FROM chat_turns WHERE user_id = $1 AND thread_id = $2 ORDER BY turn DESC LIMIT 10",
    [user.id, threadId],
  );
  const latest = recent.rows[0]?.turn ?? 0;
  const conflict = { error: "Your chat changed in another request. Refresh to see the latest messages." } as const;
  if (lastTurn !== latest) return conflict;

  let reply: Awaited<ReturnType<typeof modelReply>>;
  try {
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
      "SELECT stock_snapshot FROM chat_turns WHERE user_id = $1 AND thread_id = $2 AND stock_snapshot IS NOT NULL ORDER BY turn DESC LIMIT 1",
      [user.id, threadId],
    );
    reply = await modelReply(
      question.trim(),
      recent.rows.reverse().map(({ question, answer }) => ({ question, answer })),
      snapshot ?? undefined,
      previous.rows[0]?.news_snapshot,
      stock.rows[0]?.stock_snapshot,
    );
  } catch {
    return { error: "The assistant is unavailable. Please try again shortly." } as const;
  }

  const saved = await authPool.query<ChatTurn>(
    `INSERT INTO chat_turns (user_id, thread_id, turn, question, answer, news_snapshot, stock_snapshot) VALUES ($1, $2, $3, $4, $5, $6, $7)
     ON CONFLICT (user_id, thread_id, turn) DO NOTHING RETURNING turn, question, answer`,
    [user.id, threadId, latest + 1, question.trim(), reply.answer, reply.news, reply.stock],
  );
  if (!saved.rowCount) return conflict;
  return { saved: saved.rows[0] } as const;
}
