export type Asset = "SPY" | "TLT";
export type Persona = "Robert" | "Amira" | "Mateo";
export type LimitStatus = "within" | "at" | "beyond";
export type Settings = {
  weights: Record<Asset, number>;
  asset: Asset;
  shock_pct: number;
  loss_limit_pct: number;
  start: string;
  end: string;
  principal: number;
  currency: "USD";
};
export type Replay = {
  total_return_pct: number;
  volatility_pct: number;
  max_drawdown_pct: number;
  peak: string;
  trough: string;
  drawdown_status: LimitStatus;
  series: { date: string; usd: number }[];
  contributions_pp: Record<Asset, number>;
  correlation: number | null;
  retrieved: Record<Asset, string>;
  sources: Record<Asset, string>;
  trading_days: number;
  baseline: string;
  last_close: string;
};
export type Analysis = {
  scenario: {
    impact_pct: number;
    impact_usd: number;
    limit_usd: number;
    threshold_shock_pct: number | null;
    can_exceed: boolean;
    status: LimitStatus;
  };
  replay: Replay | null;
  replay_error: string | null;
};
export const percent = (n: number) => `${Number(n.toFixed(3))}%`;
export const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
export const statusLabel: Record<LimitStatus, string> = {
  within: "Within limit",
  at: "At the limit",
  beyond: "Limit exceeded",
};
