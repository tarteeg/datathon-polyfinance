"use client";

import { useState, type FormEvent } from "react";

import {
  currencyOptions,
  esgOptions,
  experienceOptions,
  objectiveOptions,
  questions,
  riskToleranceOptions,
  secondaryObjectiveOptions,
  sectorOptions,
} from "@/lib/investor-questions";

import {
  investorSubmissionSchema,
  type InvestorRecord,
} from "@/lib/investor-schema";


type HoldingDraft = {
  ticker: string;
  quantity: string;
  marketValue: string;
};


type Draft = {
  age: string;
  occupation: string;
  experience: string;

  riskTolerance: string;
  horizonYears: string;
  primaryObjective: string;
  secondaryObjectives: string[];

  sectors: string[];
  otherSectors: string;
  cryptoInterest: "" | "yes" | "no";
  esgPriority: string;

  avoidExclusiveTech: "" | "yes" | "no";
  maxSinglePositionPercent: string;
  maxSectorPercent: string;
  liquidityRequirement: string;

  baseCurrency: string;
  holdings: HoldingDraft[];
  valuationLocal: string;
};


const initialDraft: Draft = {
  age: "",
  occupation: "",
  experience: "",

  riskTolerance: "",
  horizonYears: "",
  primaryObjective: "",
  secondaryObjectives: [],

  sectors: [],
  otherSectors: "",
  cryptoInterest: "",
  esgPriority: "not_specified",

  avoidExclusiveTech: "",
  maxSinglePositionPercent: "",
  maxSectorPercent: "",
  liquidityRequirement: "",

  baseCurrency: "",
  holdings: [],
  valuationLocal: "",
};


// Styling
const inputStyle =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-foreground";

const sectionStyle =
  "space-y-5 rounded-xl border border-border p-5";


export default function RiskOnboardingPage() {

  const [draft, setDraft] = useState<Draft>(initialDraft);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [investorJson, setInvestorJson] =
    useState<InvestorRecord | null>(null);

  const [copied, setCopied] = useState(false);


  function setField<K extends keyof Draft>(
    key: K,
    value: Draft[K]
  ) {
    setDraft(previous => ({
      ...previous,
      [key]: value,
    }));

    setInvestorJson(null);
    setCopied(false);
  }


  function toggleSelection(
    key: "secondaryObjectives" | "sectors",
    value: string
  ) {
    setDraft(previous => ({
      ...previous,

      [key]: previous[key].includes(value)
        ? previous[key].filter(item => item !== value)
        : [...previous[key], value],
    }));

    setInvestorJson(null);
    setCopied(false);
  }


  function updateHolding(
    index: number,
    key: keyof HoldingDraft,
    value: string
  ) {
    setDraft(previous => ({
      ...previous,

      holdings: previous.holdings.map((holding, i) =>
        i === index
          ? { ...holding, [key]: value }
          : holding
      ),
    }));

    setInvestorJson(null);
    setCopied(false);
  }


  // Submit the completed questionnaire
  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setError("");
    setInvestorJson(null);

    // Both yes/no questions require an explicit answer
    if (
      draft.cryptoInterest === "" ||
      draft.avoidExclusiveTech === ""
    ) {
      setError(
        "Please answer the cryptocurrency and technology-diversification questions."
      );
      return;
    }


    // Convert optional valuation date into ISO format
    let valuationTimestamp: string | null = null;

    if (draft.valuationLocal) {
      const timestamp = new Date(draft.valuationLocal);

      if (Number.isNaN(timestamp.getTime())) {
        setError("Invalid portfolio valuation date.");
        return;
      }

      valuationTimestamp = timestamp.toISOString();
    }


    // Combine predefined and custom sectors
    const customSectors = draft.otherSectors
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);

    const sectors = [
      ...new Set([...draft.sectors, ...customSectors]),
    ];


    const optionalFraction = (value: string) =>
      value.trim() === ""
        ? null
        : Number(value) / 100;


    const submission = {

      profile: {
        age: Number(draft.age),
        occupation: draft.occupation,
        investment_experience: draft.experience,
      },

      investment_policy: {

        risk_tolerance: draft.riskTolerance,

        investment_horizon_years:
          Number(draft.horizonYears),

        primary_objective:
          draft.primaryObjective,

        secondary_objectives:
          draft.secondaryObjectives,

        preferences: {

          sectors_of_interest: sectors,

          crypto_interest:
            draft.cryptoInterest === "yes",

          esg_priority:
            draft.esgPriority,

        },

        constraints: {

          avoid_exclusive_technology_exposure:
            draft.avoidExclusiveTech === "yes",

          max_single_position_weight:
            optionalFraction(
              draft.maxSinglePositionPercent
            ),

          max_sector_weight:
            optionalFraction(
              draft.maxSectorPercent
            ),

          liquidity_requirement:
            draft.liquidityRequirement.trim() || null,

        },

      },

      portfolio: {

        base_currency: draft.baseCurrency,

        holdings: draft.holdings.map(holding => ({

          ticker: holding.ticker.trim().toUpperCase(),

          quantity: Number(holding.quantity),

          market_value:
            holding.marketValue.trim() === ""
              ? null
              : Number(holding.marketValue),

        })),

        valuation_timestamp: valuationTimestamp,

      },

    };


    // Validate the submission
    const validation =
      investorSubmissionSchema.safeParse(submission);

    if (!validation.success) {

      const issue = validation.error.issues[0];

      setError(
        `Check ${issue.path.join(".") || "your answers"}: ${issue.message}`
      );

      return;
    }


    // Send validated data to our Next.js API
    setIsSubmitting(true);

    try {

      const response = await fetch(
        "/api/risk-questionnaire",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify(validation.data),
        }
      );


      const result: {
        investor?: InvestorRecord;
        error?: string;
      } = await response.json().catch(() => ({}));


      if (!response.ok || !result.investor) {
        throw new Error(
          result.error ?? "Unable to generate investor JSON."
        );
      }


      // Store generated JSON for preview
      setInvestorJson(result.investor);
      setCopied(false);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to generate investor JSON."
      );

    } finally {

      setIsSubmitting(false);

    }
  }


  // Copy JSON to clipboard
  async function copyJson() {

    if (!investorJson) return;

    try {

      await navigator.clipboard.writeText(
        JSON.stringify(investorJson, null, 2)
      );

      setCopied(true);

    } catch {

      setError(
        "Clipboard access failed. Copy the JSON manually."
      );

    }
  }


  // Questionnaire interface
  return (
    <main className="mx-auto max-w-3xl space-y-6 px-4 py-8 text-foreground">

      <header className="space-y-2">

        <h1 className="text-3xl font-bold">
          Investor Questionnaire
        </h1>

        <p className="text-sm text-muted-foreground">
          Tell us about your investment experience,
          objectives, preferences, and portfolio.
        </p>

      </header>


      <form
        onSubmit={handleSubmit}
        className="space-y-6"
      >

        <fieldset
          disabled={isSubmitting}
          className="space-y-6"
        >

          {/* SECTION 1: INVESTOR PROFILE */}

          <section className={sectionStyle}>

            <h2 className="text-xl font-semibold">
              1. Investor Profile
            </h2>

            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.age} *
              </span>

              <input
                type="number"
                min="1"
                max="120"
                step="1"
                required
                className={inputStyle}
                value={draft.age}
                onChange={e =>
                  setField("age", e.target.value)
                }
              />

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.occupation} *
              </span>

              <input
                type="text"
                maxLength={120}
                required
                className={inputStyle}
                value={draft.occupation}
                onChange={e =>
                  setField("occupation", e.target.value)
                }
                placeholder="e.g. Software engineer"
              />

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.investmentExperience} *
              </span>

              <select
                required
                className={inputStyle}
                value={draft.experience}
                onChange={e =>
                  setField("experience", e.target.value)
                }
              >

                <option value="">
                  Select your experience
                </option>

                {experienceOptions.map(option => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}

              </select>

            </label>

          </section>



          {/* SECTION 2: INVESTMENT POLICY */}

          <section className={sectionStyle}>

            <h2 className="text-xl font-semibold">
              2. Investment Policy
            </h2>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.riskTolerance} *
              </span>

              <select
                required
                className={inputStyle}
                value={draft.riskTolerance}
                onChange={e =>
                  setField("riskTolerance", e.target.value)
                }
              >

                <option value="">
                  Select risk tolerance
                </option>

                {riskToleranceOptions.map(option => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}

              </select>

              <p className="text-xs text-muted-foreground">
                Select your own tolerance.
                It is not inferred from your age or occupation.
              </p>

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.investmentHorizon} *
              </span>

              <input
                type="number"
                min="0.1"
                max="100"
                step="any"
                required
                className={inputStyle}
                value={draft.horizonYears}
                onChange={e =>
                  setField("horizonYears", e.target.value)
                }
                placeholder="e.g. 15"
              />

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.primaryObjective} *
              </span>

              <select
                required
                className={inputStyle}
                value={draft.primaryObjective}
                onChange={e =>
                  setField("primaryObjective", e.target.value)
                }
              >

                <option value="">
                  Select objective
                </option>

                {objectiveOptions.map(option => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}

              </select>

            </label>


            <div className="space-y-2">

              <p className="text-sm font-medium">
                {questions.secondaryObjectives}
              </p>

              <div className="grid gap-2 sm:grid-cols-2">

                {secondaryObjectiveOptions.map(option => (
                  <label
                    key={option.value}
                    className="flex items-center gap-2 text-sm"
                  >

                    <input
                      type="checkbox"
                      checked={draft.secondaryObjectives.includes(
                        option.value
                      )}
                      onChange={() =>
                        toggleSelection(
                          "secondaryObjectives",
                          option.value
                        )
                      }
                    />

                    {option.label}

                  </label>
                ))}

              </div>

            </div>

          </section>



          {/* SECTION 3: PREFERENCES */}

          <section className={sectionStyle}>

            <h2 className="text-xl font-semibold">
              3. Investment Preferences
            </h2>


            <div className="space-y-2">

              <p className="text-sm font-medium">
                {questions.sectorsOfInterest}
              </p>

              <div className="grid gap-2 sm:grid-cols-2">

                {sectorOptions.map(sector => (
                  <label
                    key={sector}
                    className="flex items-center gap-2 text-sm"
                  >

                    <input
                      type="checkbox"
                      checked={draft.sectors.includes(sector)}
                      onChange={() =>
                        toggleSelection("sectors", sector)
                      }
                    />

                    {sector}

                  </label>
                ))}

              </div>


              <label className="block space-y-1 pt-2">

                <span className="text-sm">
                  Other sectors (comma-separated)
                </span>

                <input
                  type="text"
                  className={inputStyle}
                  value={draft.otherSectors}
                  onChange={e =>
                    setField("otherSectors", e.target.value)
                  }
                  placeholder="e.g. aerospace, biotechnology"
                />

              </label>

            </div>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.cryptoInterest} *
              </span>

              <select
                required
                className={inputStyle}
                value={draft.cryptoInterest}
                onChange={e =>
                  setField(
                    "cryptoInterest",
                    e.target.value as Draft["cryptoInterest"]
                  )
                }
              >

                <option value="">
                  Select an answer
                </option>

                <option value="yes">Yes</option>
                <option value="no">No</option>

              </select>

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.esgPriority}
              </span>

              <select
                className={inputStyle}
                value={draft.esgPriority}
                onChange={e =>
                  setField("esgPriority", e.target.value)
                }
              >

                {esgOptions.map(option => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}

              </select>

            </label>

          </section>



          {/* SECTION 4: CONSTRAINTS */}

          <section className={sectionStyle}>

            <h2 className="text-xl font-semibold">
              4. Investment Constraints
            </h2>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.avoidExclusiveTechnologyExposure} *
              </span>

              <select
                required
                className={inputStyle}
                value={draft.avoidExclusiveTech}
                onChange={e =>
                  setField(
                    "avoidExclusiveTech",
                    e.target.value as Draft["avoidExclusiveTech"]
                  )
                }
              >

                <option value="">
                  Select an answer
                </option>

                <option value="yes">Yes</option>
                <option value="no">No</option>

              </select>

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.maxSinglePositionWeight}
              </span>

              <input
                type="number"
                min="0"
                max="100"
                step="any"
                className={inputStyle}
                value={draft.maxSinglePositionPercent}
                onChange={e =>
                  setField(
                    "maxSinglePositionPercent",
                    e.target.value
                  )
                }
                placeholder="Leave blank if unspecified"
              />

              <p className="text-xs text-muted-foreground">
                Enter a percentage (0–100).
                Blank means no limit was specified.
              </p>

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.maxSectorWeight}
              </span>

              <input
                type="number"
                min="0"
                max="100"
                step="any"
                className={inputStyle}
                value={draft.maxSectorPercent}
                onChange={e =>
                  setField("maxSectorPercent", e.target.value)
                }
                placeholder="Leave blank if unspecified"
              />

            </label>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.liquidityRequirement}
              </span>

              <textarea
                className={inputStyle}
                rows={2}
                maxLength={500}
                value={draft.liquidityRequirement}
                onChange={e =>
                  setField(
                    "liquidityRequirement",
                    e.target.value
                  )
                }
                placeholder="Leave blank if none specified"
              />

            </label>

          </section>



          {/* SECTION 5: PORTFOLIO */}

          <section className={sectionStyle}>

            <h2 className="text-xl font-semibold">
              5. Portfolio Information
            </h2>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.baseCurrency} *
              </span>

              <select
                required
                className={inputStyle}
                value={draft.baseCurrency}
                onChange={e =>
                  setField("baseCurrency", e.target.value)
                }
              >

                <option value="">
                  Select a currency
                </option>

                {currencyOptions.map(currency => (
                  <option
                    key={currency}
                    value={currency}
                  >
                    {currency}
                  </option>
                ))}

              </select>

            </label>


            <div className="space-y-3">

              <p className="text-sm font-medium">
                {questions.holdings}
              </p>

              <p className="text-xs text-muted-foreground">
                Add each asset's ticker and quantity.
                Total market value is optional and must be
                expressed in your selected base currency.
              </p>


              {draft.holdings.map((holding, index) => (

                <div
                  key={index}
                  className="grid gap-2 rounded-md border border-border p-3 sm:grid-cols-3"
                >

                  <label className="space-y-1 text-sm">

                    Ticker *

                    <input
                      className={inputStyle}
                      value={holding.ticker}
                      onChange={e =>
                        updateHolding(
                          index,
                          "ticker",
                          e.target.value.toUpperCase()
                        )
                      }
                      placeholder="NVDA"
                      required
                    />

                  </label>


                  <label className="space-y-1 text-sm">

                    Quantity *

                    <input
                      className={inputStyle}
                      type="number"
                      min="0.00000001"
                      step="any"
                      required
                      value={holding.quantity}
                      onChange={e =>
                        updateHolding(
                          index,
                          "quantity",
                          e.target.value
                        )
                      }
                    />

                  </label>


                  <label className="space-y-1 text-sm">

                    Total market value (optional)

                    <input
                      className={inputStyle}
                      type="number"
                      min="0"
                      step="any"
                      value={holding.marketValue}
                      onChange={e =>
                        updateHolding(
                          index,
                          "marketValue",
                          e.target.value
                        )
                      }
                      placeholder="Unknown"
                    />

                  </label>


                  <button
                    type="button"
                    className="text-left text-sm underline"
                    onClick={() =>
                      setField(
                        "holdings",
                        draft.holdings.filter(
                          (_, i) => i !== index
                        )
                      )
                    }
                  >
                    Remove holding
                  </button>

                </div>
              ))}


              <button
                type="button"
                className="rounded-md border border-border px-3 py-2 text-sm"
                onClick={() =>
                  setField("holdings", [
                    ...draft.holdings,
                    {
                      ticker: "",
                      quantity: "",
                      marketValue: "",
                    },
                  ])
                }
              >
                + Add holding
              </button>

            </div>


            <label className="block space-y-1">

              <span className="text-sm font-medium">
                {questions.valuationTimestamp}
              </span>

              <input
                className={inputStyle}
                type="datetime-local"
                value={draft.valuationLocal}
                onChange={e =>
                  setField("valuationLocal", e.target.value)
                }
              />

              <p className="text-xs text-muted-foreground">
                Optional. Only enter the actual valuation
                date and time. Leave blank if unknown.
              </p>

            </label>

          </section>

        </fieldset>



        {/* ERROR MESSAGE */}

        {error && (

          <p
            role="alert"
            className="rounded-md border border-red-500 p-3 text-sm text-red-600"
          >
            {error}
          </p>

        )}



        {/* SUBMIT BUTTON */}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg bg-primary px-4 py-3 font-semibold text-primary-foreground disabled:opacity-50"
        >

          {isSubmitting
            ? "Saving Investor Profile..."
            : "Save Investor Profile"}
        </button>

      </form>



      {/* JSON RESULT */}

      {investorJson && (

        <section className="space-y-3 rounded-xl border border-border p-5">

          <h2 className="text-xl font-semibold">
            Generated Investor Record
          </h2>

          <p className="text-sm text-muted-foreground">
            Your investor profile has been saved successfully.
          </p>


          <button
            type="button"
            onClick={copyJson}
            className="rounded-md border border-border px-3 py-2 text-sm"
          >

            {copied ? "Copied!" : "Copy JSON"}

          </button>


          <pre className="max-h-96 overflow-auto rounded-md bg-muted p-3 text-xs">

            {JSON.stringify(investorJson, null, 2)}

          </pre>

        </section>

      )}

    </main>
  );
}
