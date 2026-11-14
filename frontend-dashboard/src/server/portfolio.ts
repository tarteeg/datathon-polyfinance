import "server-only";
import { cache } from "react";
import { authPool } from "@/lib/db";
import { requireSession } from "@/lib/session";

export const getHoldings = cache(async () => {
  const { user } = await requireSession();
  const result = await authPool.query<{ ticker: string; quantity: string | null }>(
    "SELECT ticker, quantity FROM portfolio_holdings WHERE user_id = $1 ORDER BY ticker",
    [user.id],
  );
  return result.rows;
});
