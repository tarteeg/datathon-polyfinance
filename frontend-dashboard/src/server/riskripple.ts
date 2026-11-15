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

export type AlertMatch = {
  symbol: string;
  relationship: string;
  matched_entity: string;
  evidence_snippet: string;
  classification: string;
  verification_reasoning?: string | null;
  is_confirmed_alert: boolean;
  recommendation: string | null;
  recommendation_error: string | null;
};

export type AlertEntry = {
  user_id: string;
  document_number: string | null;
  title: string | null;
  publication_date: string | null;
  document_url: string | null;
  matches: AlertMatch[];
};

export type AlertScanResponse = {
  alerts: AlertEntry[];
};

async function postAlertScan(path: string, tickers: string[], userId: string): Promise<AlertEntry[]> {
  const backend = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const response = await fetch(new URL(path, backend), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ portfolio_holdings: tickers, user_id: userId }),
    cache: "no-store",
    // A scan can run the recommendation/verification step across several real
    // matches; give it real room, same as the manual investigate call.
    signal: AbortSignal.timeout(150000),
  });
  if (!response.ok) throw new Error(`Alert scan request failed (${response.status})`);
  const data = (await response.json()) as AlertScanResponse;
  return data.alerts;
}

/** Real Federal Register / regulatory documents checked against this user's real holdings. */
export async function scanRegulatoryAlerts(tickers: string[], userId: string): Promise<AlertEntry[]> {
  return postAlertScan("/riskripple/alerts/scan", tickers, userId);
}

/** Real StocksFeed news, per held ticker, checked against this user's real holdings. */
export async function scanNewsAlerts(tickers: string[], userId: string): Promise<AlertEntry[]> {
  return postAlertScan("/riskripple/alerts/scan-news", tickers, userId);
}
