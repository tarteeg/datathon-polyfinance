"use server";

import { refresh } from "next/cache";

import { sp500 } from "@/data/sp500";
import { authPool } from "@/lib/db";
import { requireSession } from "@/lib/session";

function quantityError(quantity: string) {
  if (quantity && (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(quantity) || !/[1-9]/.test(quantity))) {
    return "Enter a positive share count or leave it blank.";
  }
}

export async function addPortfolioStock(form: FormData) {
  const { user } = await requireSession();
  const ticker = String(form.get("ticker") ?? "")
    .trim()
    .toUpperCase();
  const quantity = String(form.get("quantity") ?? "").trim();

  if (!Object.hasOwn(sp500, ticker)) return { error: "Select an S&P 500 stock." };
  const error = quantityError(quantity);
  if (error) return { error };

  try {
    const result = await authPool.query(
      "INSERT INTO portfolio_holdings (user_id, ticker, quantity) VALUES ($1, $2, $3) ON CONFLICT (user_id, ticker) DO NOTHING",
      [user.id, ticker, quantity || null],
    );
    if (!result.rowCount) return { error: `${ticker} is already in your portfolio.` };
  } catch {
    return { error: "Couldn’t save the stock. Try again." };
  }
  refresh();
  return { ticker };
}

export async function updatePortfolioShares(ticker: string, quantity: string) {
  const { user } = await requireSession();
  quantity = quantity.trim();
  const error = quantityError(quantity);
  if (error) return { error };

  try {
    const result = await authPool.query(
      "UPDATE portfolio_holdings SET quantity = $1 WHERE user_id = $2 AND ticker = $3",
      [quantity || null, user.id, ticker],
    );
    if (!result.rowCount) return { error: "This stock is no longer in your portfolio." };
  } catch {
    return { error: "Couldn’t save your shares. Try again." };
  }
  refresh();
  return { error: null };
}
