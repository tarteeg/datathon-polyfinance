type SamplePortfolio = {
  name: string;
  theme: string;
  weights: Record<string, number>;
};

export const samplePortfolios: SamplePortfolio[] = [
  {
    name: "Magnificent Tech",
    theme: "Big Tech and AI",
    weights: { NVDA: 25, MSFT: 25, AAPL: 20, GOOGL: 15, AMZN: 15 },
  },
  {
    name: "AI & Semiconductors",
    theme: "AI infrastructure and computing",
    weights: { NVDA: 30, AVGO: 25, AMD: 20, MSFT: 15, ORCL: 10 },
  },
  {
    name: "Wall Street Giants",
    theme: "Banking, investment banking, and payments",
    weights: { JPM: 30, BAC: 20, GS: 20, MS: 15, V: 15 },
  },
  {
    name: "Defensive Blue Chips",
    theme: "Established consumer and healthcare companies",
    weights: { PG: 25, KO: 20, PEP: 20, JNJ: 20, WMT: 15 },
  },
  {
    name: "Healthcare Innovators",
    theme: "Pharmaceuticals and medical technology",
    weights: { LLY: 30, ABBV: 20, JNJ: 20, MRK: 15, ISRG: 15 },
  },
  {
    name: "Energy Titans",
    theme: "Oil, gas, and energy services",
    weights: { XOM: 30, CVX: 25, COP: 20, SLB: 15, EOG: 10 },
  },
  {
    name: "Consumer Economy",
    theme: "Retail, consumption, and household spending",
    weights: { AMZN: 25, COST: 20, WMT: 20, HD: 20, MCD: 15 },
  },
  {
    name: "High-Risk Growth",
    theme: "Concentrated high-growth technology",
    weights: { TSLA: 35, PLTR: 25, NVDA: 25, AMD: 15 },
  },
  {
    name: "Industrial America",
    theme: "Manufacturing, infrastructure, and aerospace",
    weights: { CAT: 25, DE: 25, HON: 20, GE: 15, RTX: 15 },
  },
  {
    name: "Diversified Giants",
    theme: "Multiple industries",
    weights: { MSFT: 15, JPM: 15, JNJ: 15, PG: 15, XOM: 15, WMT: 15, CAT: 10 },
  },
  {
    name: "Dividend-Oriented",
    theme: "Established dividend-paying companies",
    weights: { KO: 20, PG: 20, JNJ: 20, XOM: 20, VZ: 20 },
  },
  {
    name: "Entertainment & Digital",
    theme: "Entertainment, digital advertising, and gaming",
    weights: { NFLX: 30, DIS: 25, META: 20, GOOGL: 15, TTWO: 10 },
  },
];
