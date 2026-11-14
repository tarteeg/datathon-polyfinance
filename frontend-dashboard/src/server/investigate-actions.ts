"use server";

import { requireSession } from "@/lib/session";
import { investigate, type InvestigateResult } from "@/server/riskripple";

export type RunInvestigationResult = { ok: true; data: InvestigateResult } | { ok: false; error: string };

export async function runInvestigation(form: FormData): Promise<RunInvestigationResult> {
  await requireSession();

  const eventDescription = String(form.get("event_description") ?? "").trim();
  const tickers = String(form.get("tickers") ?? "")
    .split(",")
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean);

  if (!eventDescription) return { ok: false, error: "Describe the event or scenario to investigate." };
  if (!tickers.length) return { ok: false, error: "Enter at least one portfolio ticker." };

  try {
    const data = await investigate(eventDescription, tickers);
    return { ok: true, data };
  } catch {
    return { ok: false, error: "Couldn’t reach the investigation agent. Try again." };
  }
}
