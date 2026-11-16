export const questions = {
  age: "How old are you?",

  occupation: "What is your occupation?",

  investmentExperience:
    "How much investing experience do you have?",

  riskTolerance:
    "How much investment risk are you willing to accept?",

  investmentHorizon:
    "For how many years do you plan to keep your money invested?",

  primaryObjective:
    "What is your primary investment objective?",

  secondaryObjectives:
    "What are your secondary investment objectives? Select all that apply.",

  sectorsOfInterest:
    "Which sectors or investment themes interest you?",

  cryptoInterest:
    "Are you interested in cryptocurrency investments?",

  esgPriority:
    "How important are environmental, social, and governance (ESG) considerations to you?",

  avoidExclusiveTechnologyExposure:
    "Do you want to avoid investing exclusively in technology companies?",

  maxSinglePositionWeight:
    "Do you have a maximum percentage you would allocate to a single investment?",

  maxSectorWeight:
    "Do you have a maximum percentage you would allocate to one sector?",

  liquidityRequirement:
    "Do you have any specific requirements for accessing your invested money?",

  baseCurrency:
    "What is your portfolio's base currency?",

  holdings:
    "What investments do you currently own?",

  valuationTimestamp:
    "When were your portfolio's market values last determined?",
} as const;


// Investor experience
export const experienceOptions = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
] as const;


// Risk tolerance
export const riskToleranceOptions = [
  {
    value: "low",
    label: "Low — I prefer stability and capital preservation",
  },
  {
    value: "moderate",
    label: "Moderate — I accept some investment volatility",
  },
  {
    value: "high",
    label: "High — I accept significant investment volatility",
  },
] as const;


// Primary investment objectives
export const objectiveOptions = [
  {
    value: "capital_preservation",
    label: "Capital preservation",
  },
  {
    value: "balanced_growth",
    label: "Balanced capital growth",
  },
  {
    value: "long_term_growth",
    label: "Long-term capital growth",
  },
  {
    value: "income",
    label: "Regular investment income",
  },
  {
    value: "short_term_growth",
    label: "Short-term capital growth",
  },
] as const;


// Secondary investment objectives
export const secondaryObjectiveOptions = [
  { value: "diversification", label: "Diversification" },
  { value: "income", label: "Additional income" },
  { value: "capital_preservation", label: "Capital preservation" },
  { value: "inflation_protection", label: "Inflation protection" },
  { value: "esg_alignment", label: "ESG alignment" },
  { value: "liquidity", label: "Liquidity" },
] as const;


// Investment sectors and themes
export const sectorOptions = [
  "AI",
  "technology",
  "healthcare",
  "financials",
  "energy",
  "industrials",
  "consumer_goods",
  "utilities",
  "real_estate",
  "materials",
] as const;


// ESG preferences
export const esgOptions = [
  {
    value: "not_specified",
    label: "Not specified / no particular preference",
  },
  {
    value: "low",
    label: "Low priority",
  },
  {
    value: "moderate",
    label: "Moderate priority",
  },
  {
    value: "high",
    label: "High priority",
  },
] as const;


// Portfolio currencies
export const currencyOptions = [
  "USD",
  "CAD",
  "EUR",
  "GBP",
  "CHF",
  "AUD",
  "JPY",
] as const;
