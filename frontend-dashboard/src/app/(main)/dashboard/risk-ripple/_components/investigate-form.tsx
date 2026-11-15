"use client";

import { Loader2, Search } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { runInvestigation } from "@/server/investigate-actions";
import type { InvestigateResult } from "@/server/riskripple";

import { FindingsCards } from "./findings-cards";

export type Prefill = { eventDescription: string; tickers: string };

export function InvestigateForm({
  defaultTickers,
  prefill,
  onComplete,
}: {
  defaultTickers: string;
  prefill?: Prefill | null;
  onComplete?: () => void;
}) {
  const id = useId();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<InvestigateResult | null>(null);

  // Remount the form when a new prefill arrives (e.g. "Investigate Impact" from a
  // news article) so the uncontrolled defaultValue inputs below pick it up.
  return (
    <div key={prefill ? `${prefill.eventDescription}-${prefill.tickers}` : "default"} className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Describe the event</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-4"
            onSubmit={async (event) => {
              event.preventDefault();
              if (pending) return;
              const form = new FormData(event.currentTarget);
              setPending(true);
              setError("");
              setResult(null);
              try {
                const outcome = await runInvestigation(form);
                if (!outcome.ok) {
                  setError(outcome.error);
                } else if (outcome.data.error) {
                  setError(outcome.data.error);
                } else {
                  // This is the live/current session's result -- past investigations
                  // live on their own page now, so showing it here is no longer a
                  // duplicate.
                  setResult(outcome.data);
                  onComplete?.();
                }
              } catch {
                setError("Couldn’t reach the investigation agent. Try again.");
              } finally {
                setPending(false);
              }
            }}
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor={`${id}-event`}>Event or scenario</FieldLabel>
                <Textarea
                  id={`${id}-event`}
                  name="event_description"
                  rows={3}
                  defaultValue={prefill?.eventDescription}
                  placeholder="e.g. New export controls restrict advanced semiconductor equipment sales to a major chip-manufacturing hub."
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor={`${id}-tickers`}>Portfolio holdings (tickers)</FieldLabel>
                <Input
                  id={`${id}-tickers`}
                  name="tickers"
                  defaultValue={prefill?.tickers || defaultTickers}
                  placeholder="NVDA, AMD, INTC"
                  required
                />
              </Field>
            </FieldGroup>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <Button type="submit" disabled={pending} className="self-start">
              {pending ? <Loader2 className="animate-spin" /> : <Search />}
              {pending ? "Investigating…" : "Investigate"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && !result.error && (
        <Card>
          <CardHeader>
            <CardTitle>Findings</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FindingsCards result={result} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
