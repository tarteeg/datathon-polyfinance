"use server";

import { revalidatePath } from "next/cache";
import type { PoolClient } from "pg";

import { samplePortfolios } from "@/data/sample-portfolios";
import { authPool } from "@/lib/db";
import { requireSession } from "@/lib/session";
import { fetchHistory } from "@/server/stock-history";

export async function replaceSamplePortfolio(name: string, amount: string) {
  const { user } = await requireSession();
  const sample = samplePortfolios.find((entry) => entry.name === name);
  if (!sample) return { error: "Choose a sample portfolio." };
  const value = Number(amount);
  if (
    !(typeof amount === "string" && /^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/.test(amount)) ||
    value <= 0 ||
    !Number.isSafeInteger(Math.round(value * 100))
  ) {
    return { error: "Enter a positive USD amount with up to two decimal places." };
  }

  const tickers = Object.keys(sample.weights);
  const quantities = await Promise.all(
    tickers.map(async (ticker) => {
      const history = await fetchHistory(ticker, "1d").catch(() => null);
      const quote = history?.ticker;
      if (quote?.currency !== "USD" || !Number.isFinite(quote.regularMarketPrice) || quote.regularMarketPrice <= 0) {
        return null;
      }
      return (value * sample.weights[ticker]) / (100 * quote.regularMarketPrice);
    }),
  );
  const missing = tickers.filter((_, index) => quantities[index] === null);
  if (missing.length)
    return { error: `USD quotes unavailable for ${missing.join(", ")}. Your portfolio is unchanged.` };

  let client: PoolClient | undefined;
  try {
    client = await authPool.connect();
    await client.query("BEGIN");
    // Serialize replacements for this account, including when its portfolio starts empty.
    await client.query('SELECT id FROM "user" WHERE id = $1 FOR UPDATE', [user.id]);
    await client.query("DELETE FROM portfolio_holdings WHERE user_id = $1", [user.id]);
    await client.query(
      `INSERT INTO portfolio_holdings (user_id, ticker, quantity)
       SELECT $1, ticker, quantity FROM unnest($2::text[], $3::numeric[]) AS positions(ticker, quantity)`,
      [user.id, tickers, quantities],
    );
    await client.query("COMMIT");
  } catch {
    await client?.query("ROLLBACK");
    return { error: "Couldn’t replace your portfolio. Try again." };
  } finally {
    client?.release();
  }

  revalidatePath("/dashboard", "layout");
  return { error: null };
}
