
import { z } from "zod";

const optionalWeight = z
  .number()
  .finite()
  .min(0)
  .max(1)
  .nullable();


const holdingSchema = z.object({
  ticker: z.string()
    .trim()
    .toUpperCase()
    .regex(
      /^[A-Z0-9][A-Z0-9.^_-]{0,19}$/,
      "Enter a valid ticker symbol."
    ),

  quantity: z.number()
    .finite()
    .positive(),

  market_value: z.number()
    .finite()
    .min(0)
    .nullable(),
}).strict();


export const investorSubmissionSchema = z.object({

  profile: z.object({
    age: z.number()
      .int()
      .min(1)
      .max(120),

    occupation: z.string()
      .trim()
      .min(1)
      .max(120),

    investment_experience: z.enum([
      "beginner",
      "intermediate",
      "advanced",
    ]),
  }).strict(),


  investment_policy: z.object({

    risk_tolerance: z.enum([
      "low",
      "moderate",
      "high",
    ]),

    investment_horizon_years: z.number()
      .finite()
      .positive()
      .max(100),

    primary_objective: z.enum([
      "capital_preservation",
      "balanced_growth",
      "long_term_growth",
      "income",
      "short_term_growth",
    ]),

    secondary_objectives: z.array(z.enum([
      "diversification",
      "income",
      "capital_preservation",
      "inflation_protection",
      "esg_alignment",
      "liquidity",
    ])).max(6),


    // Preferences
    preferences: z.object({

      sectors_of_interest: z.array(
        z.string().trim().min(1).max(80)
      ).max(30),

      crypto_interest: z.boolean(),

      esg_priority: z.enum([
        "not_specified",
        "low",
        "moderate",
        "high",
      ]),

    }).strict(),


    // Constraints
    constraints: z.object({

      avoid_exclusive_technology_exposure: z.boolean(),

      max_single_position_weight: optionalWeight,

      max_sector_weight: optionalWeight,

      liquidity_requirement: z.string()
        .trim()
        .min(1)
        .max(500)
        .nullable(),

    }).strict(),

  }).strict(),


  portfolio: z.object({

    base_currency: z.enum([
      "USD",
      "CAD",
      "EUR",
      "GBP",
      "CHF",
      "AUD",
      "JPY",
    ]),

    holdings: z.array(holdingSchema).max(100),

    valuation_timestamp: z.string().refine(
      value => !Number.isNaN(Date.parse(value)),
      "Invalid valuation timestamp."
    ).nullable(),

  }).strict(),

}).strict().superRefine((input, ctx) => {

  // Prevent duplicate ticker symbols
  const seen = new Set<string>();

  input.portfolio.holdings.forEach((holding, index) => {
    if (seen.has(holding.ticker)) {
      ctx.addIssue({
        code: "custom",
        path: ["portfolio", "holdings", index, "ticker"],
        message: "Duplicate ticker symbol.",
      });
    }

    seen.add(holding.ticker);
  });

});


export type InvestorSubmission =
  z.infer<typeof investorSubmissionSchema>;


//Investor record sent to the backend
export type InvestorRecord = {

  investor_id: string;

  profile: InvestorSubmission["profile"] & {
    name: string;
  };

  investment_policy: InvestorSubmission["investment_policy"];

  portfolio: {
    base_currency: InvestorSubmission["portfolio"]["base_currency"];

    holdings: (
      InvestorSubmission["portfolio"]["holdings"][number] & {
        weight: number | null;
      }
    )[];

    valuation_timestamp: string | null;
  };
};


// Final JSON object
export function assembleInvestorRecord(
  investorId: string,
  registeredName: string,
  submission: InvestorSubmission
): InvestorRecord {

  const holdings = submission.portfolio.holdings;

  const allValued =
    holdings.length > 0 &&
    holdings.every(h => h.market_value !== null);

  const totalValue = allValued
    ? holdings.reduce(
        (total, h) => total + (h.market_value ?? 0),
        0
      )
    : 0;

  const canComputeWeights =
    allValued &&
    totalValue > 0 &&
    Number.isFinite(totalValue);

  let assignedWeight = 0;

  const weightedHoldings = holdings.map((holding, index) => {

    let weight: number | null = null;

    if (canComputeWeights) {

      if (index === holdings.length - 1) {
        weight = Number((1 - assignedWeight).toFixed(8));
      } else {
        weight = Number(
          ((holding.market_value ?? 0) / totalValue).toFixed(8)
        );

        assignedWeight += weight;
      }

    }

    return {
      ...holding,
      weight,
    };
  });


  return {

    investor_id: investorId,

    profile: {
      name: registeredName,
      ...submission.profile,
    },

    investment_policy: submission.investment_policy,

    portfolio: {
      base_currency: submission.portfolio.base_currency,
      holdings: weightedHoldings,
      valuation_timestamp: submission.portfolio.valuation_timestamp,
    },

  };
}
