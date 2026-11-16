"use client";

import { useId, useState, useTransition } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { samplePortfolios } from "@/data/sample-portfolios";
import { formatCurrency } from "@/lib/utils";
import { replaceSamplePortfolio } from "@/server/replace-sample-portfolio";

export function SamplePortfolioForm({ savedPersona }: { savedPersona?: string | null }) {
  const id = useId();
  const [name, setName] = useState(() => {
    const preferred = savedPersona ? samplePortfolios.find((entry) => entry.persona === savedPersona) : undefined;
    return (preferred ?? samplePortfolios[0]).name;
  });
  const [amount, setAmount] = useState("10000");
  const [pending, startTransition] = useTransition();
  const sample = samplePortfolios.find((entry) => entry.name === name)!;

  function apply() {
    startTransition(async () => {
      try {
        const { error } = await replaceSamplePortfolio(name, amount);
        if (error) toast.error(error);
        else toast.success(`Your portfolio now uses ${name}.`);
      } catch {
        toast.error("Couldn’t confirm the replacement. Check your portfolio before retrying.");
      }
    });
  }

  return (
    <form action={apply} className="flex flex-col items-start gap-5">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor={id}>Sample portfolio</FieldLabel>
          <NativeSelect id={id} value={name} onChange={(event) => setName(event.target.value)} disabled={pending}>
            {samplePortfolios.map((entry) => (
              <NativeSelectOption key={entry.name}>{entry.name}</NativeSelectOption>
            ))}
          </NativeSelect>
          <FieldDescription>{sample.theme}</FieldDescription>
          {sample.persona && sample.persona !== savedPersona && (
            <FieldDescription>
              {savedPersona ? <>Analysis uses your saved <span className="capitalize">{savedPersona}</span> profile.</> : "Analysis uses the general investor view."}
              {" "}Choose a profile in Investor persona to change the interpretation.
            </FieldDescription>
          )}
        </Field>
        <Field>
          <FieldLabel htmlFor={`${id}-value`}>Invested value (USD)</FieldLabel>
          <Input
            id={`${id}-value`}
            type="number"
            min="0.01"
            step="0.01"
            required
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            disabled={pending}
          />
        </Field>
      </FieldGroup>
      <table className="w-full text-sm tabular-nums">
        <caption className="sr-only">Target allocation for {name}</caption>
        <thead>
          <tr className="border-b text-muted-foreground">
            <th scope="col" className="py-2 text-left">
              Holding
            </th>
            <th scope="col" className="text-right">
              Weight
            </th>
            <th scope="col" className="text-right">
              Target value
            </th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(sample.weights).map(([ticker, weight]) => (
            <tr key={ticker} className="border-b">
              <th scope="row" className="py-2 text-left font-medium">
                {ticker}
              </th>
              <td className="text-right">{weight}%</td>
              <td className="text-right">
                {Number(amount) > 0 ? formatCurrency((Number(amount) * weight) / 100, { currency: "USD" }) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-sm text-muted-foreground">
        Applying this sample replaces all your saved holdings, including watchlist stocks. Fractional shares are
        calculated using the latest available USD quotes.
      </p>
      <Button type="submit" size="sm" disabled={pending || !amount}>
        {pending ? "Applying sample…" : "Replace my portfolio"}
      </Button>
    </form>
  );
}
