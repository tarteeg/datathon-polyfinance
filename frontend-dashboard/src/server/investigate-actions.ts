"use server";

import { randomUUID } from "node:crypto";

import { requireSession } from "@/lib/session";
import { pollInvestigation, triggerInvestigation, type PollInvestigationResult } from "@/server/riskripple";

export type TriggerInvestigationResult = { ok: true; requestId: string } | { ok: false; error: string };

export async function triggerInvestigationAction(form: FormData): Promise<TriggerInvestigationResult> {
  const { user } = await requireSession();

  const eventDescription = String(form.get("event_description") ?? "").trim();
  const tickers = String(form.get("tickers") ?? "")
    .split(",")
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean);

  if (!eventDescription) return { ok: false, error: "Describe the event or scenario to investigate." };
  if (!tickers.length) return { ok: false, error: "Enter at least one portfolio ticker." };

  const requestId = randomUUID();
  try {
    await triggerInvestigation(eventDescription, tickers, user.id, requestId, user.investorPersona);
    return { ok: true, requestId };
  } catch {
    return { ok: false, error: "Couldn’t reach the investigation agent. Try again." };
  }
}

export type PollInvestigationActionResult = { ok: true; data: PollInvestigationResult } | { ok: false };

/** Polled on an interval by the client while an investigation is in flight. A failed
 * poll returns `ok: false` -- the caller should just retry on the next tick, same
 * fail-soft discipline as the alert-scan poller. */
export async function pollInvestigationAction(requestId: string): Promise<PollInvestigationActionResult> {
  const { user } = await requireSession();
  try {
    const data = await pollInvestigation(user.id, requestId);
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}
