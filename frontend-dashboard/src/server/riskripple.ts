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

export type ExposureClassification = { tier: string; reason: string };

export type FollowupInvestigation = {
  question: string;
  tool_used: string;
  classification: string;
  summary: string;
} | null;

export type PortfolioImpact = {
  weights_are_real?: boolean;
  weights?: Record<string, number>;
  weights_disclosure?: string;
  price_errors?: Record<string, string>;
  exposure_tiers?: Record<string, string>;
  tier_shock_table?: Record<string, number>;
  scenario_portfolio_pnl_pct?: number;
  scenario_position_pnl?: Record<string, number>;
  unshocked_holdings?: string[];
  assumptions_label?: string;
  annualized_volatility?: Record<string, number | null>;
  error?: string;
};

export type PersonaComparison = {
  persona: string;
  display_name: string;
  description: string;
  constraint_violations: string[];
  esg_notes: string[];
  verdict: string;
  challenges_the_request: boolean;
};

export type InvestigateResult = {
  event_description: string;
  portfolio_holdings: string[];
  answer: string | null;
  trace: RiskRippleTraceMessage[];
  error: string | null;
  exposure_classifications?: Record<string, ExposureClassification>;
  followup_investigation?: FollowupInvestigation;
  portfolio_impact?: PortfolioImpact;
  persona_comparison?: PersonaComparison[];
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
  classification_tier?: number | null;
  exposure_mechanism?: string | null;
  verification_reasoning?: string | null;
  is_confirmed_alert: boolean;
  recommendation: string | null;
  recommendation_error: string | null;
  source?: "news" | "regulatory";
  title?: string | null;
  document_url?: string | null;
  publication_date?: string | null;
};

export type AlertEntry = {
  user_id: string;
  document_number: string | null;
  title: string | null;
  publication_date: string | null;
  document_url: string | null;
  matches: AlertMatch[];
};

export type NewsArticle = {
  title: string;
  url: string | null;
  publication_date: string | null;
  ticker: string | null;
  summary: string;
};

export type ScanStatus = "idle" | "scanning" | "error";

export type ScanDiagnostics = {
  per_ticker: Record<string, { raw_count: number; error: string | null }>;
  error: string | null;
};

/** Shape shared by both /alerts/scan and /alerts/scan-news's poll + trigger responses.
 * The regulatory path doesn't populate `articles` (only news has per-article tier-1
 * visibility) -- this app derives its "News & Geopolitical Intelligence" section from
 * the news scan's `articles` specifically, and merges both sources' `alerts` into the
 * candidate/confirmed tiers. */
export type ScanResponse = {
  alerts: AlertEntry[];
  articles: NewsArticle[];
  investigation_candidates: AlertMatch[];
  confirmed_alerts: AlertMatch[];
  diagnostics?: ScanDiagnostics;
  status: ScanStatus;
  last_success_at: string | null;
  error_message: string | null;
};

async function postScan(path: string, tickers: string[], userId: string, limitPerTicker?: number): Promise<ScanResponse> {
  const backend = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const body: Record<string, unknown> = { portfolio_holdings: tickers, user_id: userId };
  if (limitPerTicker) body.limit_per_ticker = limitPerTicker;
  const response = await fetch(new URL(path, backend), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    // This returns almost immediately now (cache + background refresh) -- generous
    // timeout only as a safety net, not because it's expected to be slow.
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw new Error(`Scan request failed (${response.status})`);
  const data = (await response.json()) as Partial<ScanResponse>;
  return {
    alerts: data.alerts ?? [],
    articles: data.articles ?? [],
    investigation_candidates: data.investigation_candidates ?? [],
    confirmed_alerts: data.confirmed_alerts ?? [],
    diagnostics: data.diagnostics,
    status: data.status ?? "idle",
    last_success_at: data.last_success_at ?? null,
    error_message: data.error_message ?? null,
  };
}

async function getScanStatus(path: string, userId: string): Promise<ScanResponse> {
  const backend = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const url = new URL(path, backend);
  url.searchParams.set("user_id", userId);
  const response = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`Scan status request failed (${response.status})`);
  const data = (await response.json()) as Partial<ScanResponse>;
  return {
    alerts: data.alerts ?? [],
    articles: data.articles ?? [],
    investigation_candidates: data.investigation_candidates ?? [],
    confirmed_alerts: data.confirmed_alerts ?? [],
    diagnostics: data.diagnostics,
    status: data.status ?? "idle",
    last_success_at: data.last_success_at ?? null,
    error_message: data.error_message ?? null,
  };
}

/** Kicks off (or returns the cached state of) a regulatory scan. Returns almost
 * immediately -- `status: "scanning"` means a background refresh just started. */
export async function triggerRegulatoryScan(tickers: string[], userId: string): Promise<ScanResponse> {
  return postScan("/riskripple/alerts/scan", tickers, userId);
}

/** Kicks off (or returns the cached state of) a news scan. Returns almost
 * immediately -- `status: "scanning"` means a background refresh just started. */
export async function triggerNewsScan(tickers: string[], userId: string): Promise<ScanResponse> {
  return postScan("/riskripple/alerts/scan-news", tickers, userId, 10);
}

export async function pollRegulatoryScan(userId: string): Promise<ScanResponse> {
  return getScanStatus("/riskripple/alerts/scan/status", userId);
}

export async function pollNewsScan(userId: string): Promise<ScanResponse> {
  return getScanStatus("/riskripple/alerts/scan-news/status", userId);
}
