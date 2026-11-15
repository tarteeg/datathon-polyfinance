import packageJson from "../../package.json";

const currentYear = new Date().getFullYear();

export const APP_CONFIG = {
  name: "PolyFinances AlphaForge",
  url: "https://studio-admin.arhamkhnz.com",
  repository: "https://github.com/arhamkhnz/next-shadcn-admin-dashboard",
  version: packageJson.version,
  copyright: `© ${currentYear}, PolyFinances AlphaForge.`,
  meta: {
    title: "PolyFinances AlphaForge: RiskRipple",
    description:
      "Multi-agent compliance watch: mobilizes public data, coordinates specialist agents to trace how regulatory events ripple through a portfolio, adapts to each persona, explains each figure with sources.",
  },
};
