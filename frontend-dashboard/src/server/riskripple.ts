import "server-only";

export type RiskRippleTraceBlock =
  | { type: "text"; text: string }
  | { type: "tool_use"; name?: string; input?: unknown }
  | { type: "tool_result"; status?: string; content: unknown }
  | { type: "unknown"; raw: unknown };

export type RiskRippleTraceMessage = {
  role?: string;
  content: RiskRippleTraceBlock[];
};

export type InvestigateResult = {
  event_description: string;
  portfolio_holdings: string[];
  answer: string | null;
  trace: RiskRippleTraceMessage[];
  error: string | null;
};

export async function investigate(eventDescription: string, tickers: string[]): Promise<InvestigateResult> {
  const backend = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const response = await fetch(new URL("/riskripple/investigate", backend), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ event_description: eventDescription, portfolio_holdings: tickers }),
    cache: "no-store",
    // The agent can make dozens of tool calls before answering; give it real room.
    signal: AbortSignal.timeout(120000),
  });
  if (!response.ok) throw new Error(`Investigation request failed (${response.status})`);
  return response.json();
}
