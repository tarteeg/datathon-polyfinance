"use server";

import { requireSession } from "@/lib/session";
import { getHoldings } from "@/server/portfolio";
import {
  deleteInvestigationHistory,
  getInvestigationHistory,
  pollNewsScan,
  pollRegulatoryScan,
  triggerNewsScan,
  triggerRegulatoryScan,
  type InvestigationHistoryEntry,
  type ScanResponse,
} from "@/server/riskripple";

export type CombinedScanState = {
  tickers: string[];
  news: ScanResponse;
  regulatory: ScanResponse;
};

const EMPTY_SCAN: ScanResponse = {
  alerts: [],
  articles: [],
  investigation_candidates: [],
  confirmed_alerts: [],
  status: "idle",
  last_success_at: null,
  error_message: null,
};

export type TriggerAlertsScanResult = { ok: true; data: CombinedScanState } | { ok: false; error: string };

/** Called once on page load. Returns almost immediately (the backend caches +
 * backgrounds the real scan work) -- the client polls `pollAlertsScan` afterward. */
export async function triggerAlertsScan(): Promise<TriggerAlertsScanResult> {
  const { user } = await requireSession();
  const holdings = await getHoldings();
  const tickers = holdings.map((h) => h.ticker);
  if (!tickers.length) {
    return { ok: true, data: { tickers: [], news: EMPTY_SCAN, regulatory: EMPTY_SCAN } };
  }

  try {
    const [regulatory, news] = await Promise.all([
      triggerRegulatoryScan(tickers, user.id, user.investorPersona),
      triggerNewsScan(tickers, user.id, user.investorPersona),
    ]);
    return { ok: true, data: { tickers, news, regulatory } };
  } catch {
    return { ok: false, error: "Couldn't reach the alert scan. Try again." };
  }
}

export type PollAlertsScanResult = { ok: true; data: { news: ScanResponse; regulatory: ScanResponse } } | { ok: false };

/** Polled on an interval while a background scan is in progress. A failed poll
 * returns `ok: false` -- the caller should keep showing its last good state and
 * just retry on the next tick, not treat this as a terminal error (confirmed live:
 * the backend's own status endpoint can occasionally be slow/flaky under load even
 * though the underlying scan completes correctly). */
export async function pollAlertsScan(): Promise<PollAlertsScanResult> {
  const { user } = await requireSession();
  try {
    const [regulatory, news] = await Promise.all([pollRegulatoryScan(user.id, user.investorPersona), pollNewsScan(user.id, user.investorPersona)]);
    return { ok: true, data: { news, regulatory } };
  } catch {
    return { ok: false };
  }
}

export type GetHistoryResult = { ok: true; data: InvestigationHistoryEntry[] } | { ok: false };

/** Previously completed manual investigations for the current user. `limit` defaults
 * to 10 (enough for the Investigations page's "most recent" preview); the dedicated
 * History page asks for the full 50-row cap instead. */
export async function getHistory(limit = 10): Promise<GetHistoryResult> {
  const { user } = await requireSession();
  try {
    const data = await getInvestigationHistory(user.id, limit);
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}

export type DeleteHistoryResult = { ok: true } | { ok: false; error: string };

export async function deleteHistoryEntry(entryId: number): Promise<DeleteHistoryResult> {
  const { user } = await requireSession();
  try {
    const deleted = await deleteInvestigationHistory(user.id, entryId);
    return deleted ? { ok: true } : { ok: false, error: "That investigation was already removed." };
  } catch {
    return { ok: false, error: "Couldn't delete that investigation. Try again." };
  }
}
