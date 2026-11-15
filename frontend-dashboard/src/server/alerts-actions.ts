"use server";

import { requireSession } from "@/lib/session";
import { getHoldings } from "@/server/portfolio";
import { scanNewsAlerts, scanRegulatoryAlerts, type AlertEntry } from "@/server/riskripple";

export type AlertCard = {
  key: string;
  symbol: string;
  title: string | null;
  documentUrl: string | null;
  publicationDate: string | null;
  source: "regulatory" | "news";
  classification: string;
  recommendation: string | null;
  isConfirmed: boolean;
};

export type RunAlertsScanResult =
  | { ok: true; confirmed: AlertCard[]; hypotheses: AlertCard[]; tickers: string[] }
  | { ok: false; error: string };

function toCards(entries: AlertEntry[], source: "regulatory" | "news"): AlertCard[] {
  const cards: AlertCard[] = [];
  for (const entry of entries) {
    for (const match of entry.matches) {
      cards.push({
        key: `${source}-${entry.document_number ?? entry.title}-${match.symbol}`,
        symbol: match.symbol,
        title: entry.title,
        documentUrl: entry.document_url,
        publicationDate: entry.publication_date,
        source,
        classification: match.classification,
        recommendation: match.recommendation,
        isConfirmed: match.is_confirmed_alert,
      });
    }
  }
  return cards;
}

export async function runAlertsScan(): Promise<RunAlertsScanResult> {
  const { user } = await requireSession();
  const holdings = await getHoldings();
  const tickers = holdings.map((h) => h.ticker);
  if (!tickers.length) return { ok: true, confirmed: [], hypotheses: [], tickers: [] };

  try {
    const [regulatory, news] = await Promise.all([
      scanRegulatoryAlerts(tickers, user.id),
      scanNewsAlerts(tickers, user.id),
    ]);

    const allCards = [...toCards(regulatory, "regulatory"), ...toCards(news, "news")];
    const confirmed = allCards.filter((c) => c.isConfirmed);
    const hypotheses = allCards.filter((c) => !c.isConfirmed);

    return { ok: true, confirmed, hypotheses, tickers };
  } catch {
    return { ok: false, error: "Couldn't reach the alert scan. Try again." };
  }
}
