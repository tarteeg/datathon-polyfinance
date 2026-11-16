"use client";

import { Loader2, Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { pollInvestigationAction, triggerInvestigationAction } from "@/server/investigate-actions";
import type { InvestigateResult } from "@/server/riskripple";

import { FindingsCards } from "./findings-cards";

export type Prefill = { eventDescription: string; tickers: string };

const POLL_INTERVAL_MS = 4000;

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
  const [requestId, setRequestId] = useState<string | null>(null);
  const pollingRef = useRef(false);

  // The agent run can take well over a minute -- too long for one blocking request
  // (confirmed live: the ECS gateway's own idle timeout returns a 504 before a
  // synchronous call could ever finish, even though the backend keeps running and
  // completes successfully regardless). Trigger returns almost immediately; this
  // polls for the real result on an interval, same pattern as the alert scans.
  useEffect(() => {
    if (!requestId) return;
    const interval = setInterval(async () => {
      if (pollingRef.current) return;
      pollingRef.current = true;
      try {
        const outcome = await pollInvestigationAction(requestId);
        if (!outcome.ok) return; // transient poll failure -- just retry next tick
        const data = outcome.data;
        if (data.status === "pending") return;
        setRequestId(null);
        setPending(false);
        if (data.status === "error") {
          setError(data.error || "Couldn’t reach the investigation agent. Try again.");
        } else if (data.error) {
          setError(data.error);
        } else {
          setResult(data);
          onComplete?.();
        }
      } finally {
        pollingRef.current = false;
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

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
                const outcome = await triggerInvestigationAction(form);
                if (!outcome.ok) {
                  setError(outcome.error);
                  setPending(false);
                } else {
                  setRequestId(outcome.requestId);
                }
              } catch {
                setError("Couldn’t reach the investigation agent. Try again.");
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
