"use server";

import type { PortfolioSnapshot } from "./_components/portfolio-breakdown";
import type { ChartSnapshot } from "./chart-snapshot";
import { type ChatActivity, savedChatAnswer } from "@/lib/chat-stream";
import { authPool } from "@/lib/db";
import { requireSession } from "@/lib/session";

export type StockPlot = {
  symbol: string;
  period: string;
  currency: string | null;
  points?: { time: number; Close: number }[];
};

export type StockSnapshot = StockPlot | { stocks: StockPlot[] };

export type ChatTurn = {
  turn: number;
  question: string;
  answer: string;
  tool_activity?: ChatActivity[];
  portfolio_snapshot?: PortfolioSnapshot | null;
  stock_snapshot?: StockSnapshot | null;
  chart_snapshot?: ChartSnapshot | null;
};

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
    "SELECT turn, question, answer, chart_snapshot, stock_snapshot, portfolio_snapshot, tool_activity FROM chat_turns WHERE user_id = $1 AND thread_id = $2 ORDER BY turn",
    [user.id, threadId],
  );
  return history.rows.map((row) => ({ ...row, answer: savedChatAnswer(row.answer) }));
}
