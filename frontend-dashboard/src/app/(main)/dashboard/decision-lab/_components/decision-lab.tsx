"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";

import { HistoricalReplay } from "./historical-replay";
import { PersonaComparison } from "./persona-comparison";
import { type Analysis, type Asset, money, type Persona, percent, type Settings, statusLabel } from "./types";

const initial: Settings = {
  weights: { SPY: 60, TLT: 40 },
  asset: "TLT",
  shock_pct: -10,
  loss_limit_pct: 5,
  principal: 10000,
  currency: "USD",
  start: "2022-01-01",
  end: "2022-12-31",
};

export function DecisionLab() {
  const [settings, setSettings] = useState(initial);
  const [persona, setPersona] = useState<Persona>("Robert");
  const [response, setResponse] = useState<{ settings: Settings | null; result?: Analysis; error?: string }>({
    settings: null,
  });
  const current = response.settings === settings ? response : { result: undefined, error: undefined };
  const { result, error } = current;
  const scenario = result?.scenario;
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const reply = await fetch("/api/decision-lab", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(settings),
          signal: controller.signal,
        });
        if (!reply.ok) {
          const problem = await reply.json().catch(() => null);
          throw new Error(problem?.detail?.[0]?.msg ?? "Could not load the analysis. Check the connection and retry.");
        }
        const data: Analysis = await reply.json();
        if (!controller.signal.aborted) setResponse({ settings, result: data });
      } catch (cause) {
        if (!controller.signal.aborted)
          setResponse({ settings, error: cause instanceof Error ? cause.message : "Analysis unavailable." });
      }
    }, 120);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [settings]);

  function update(patch: Partial<Settings>) {
    setSettings((old) => ({ ...old, ...patch }));
  }
  function reload() {
    setResponse({ settings: null });
    update({});
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Find the breaking point</CardTitle>
          <CardDescription>
            Instantaneous hypothetical shock · Fictional {money(settings.principal)} USD portfolio
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 lg:grid-cols-2">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="shock-asset">Holding under stress</FieldLabel>
              <NativeSelect
                id="shock-asset"
                value={settings.asset}
                onChange={(e) => update({ asset: e.target.value as Asset })}
              >
                <NativeSelectOption value="TLT">TLT · Long-term US Treasury bonds</NativeSelectOption>
                <NativeSelectOption value="SPY">SPY · US large-cap stocks</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="shock">
                Price decline in {settings.asset} · {percent(-settings.shock_pct)}
              </FieldLabel>
              <input
                className="accent-primary w-full cursor-pointer"
                id="shock"
                type="range"
                min="0"
                max="100"
                step="0.5"
                value={-settings.shock_pct}
                onChange={(e) => update({ shock_pct: -Number(e.target.value) })}
              />
              <div className="text-muted-foreground flex justify-between text-xs">
                <span>0% decline</span>
                <span>100% decline</span>
              </div>
            </Field>
            <Field>
              <FieldLabel htmlFor="loss-limit">Portfolio loss limit (%)</FieldLabel>
              <Input
                id="loss-limit"
                type="number"
                min="0.01"
                max="100"
                step="0.01"
                value={settings.loss_limit_pct || ""}
                onChange={(e) => update({ loss_limit_pct: Number(e.target.value) })}
              />
            </Field>
          </FieldGroup>
          <div className="bg-muted/45 flex flex-col justify-center gap-3 rounded-lg p-5" aria-live="polite">
            {scenario && (
              <>
                <span className="text-muted-foreground text-sm">Simulated portfolio change</span>
                <strong className="text-4xl tracking-tight tabular-nums">{money(scenario.impact_usd)}</strong>
                <div className="flex items-center gap-2">
                  <span>{percent(scenario.impact_pct)}</span>
                  <Badge variant={scenario.status === "beyond" ? "destructive" : "secondary"}>
                    {statusLabel[scenario.status]}
                  </Badge>
                </div>
                <p>
                  {scenario.threshold_shock_pct === null ? (
                    `Even a 100% drop in ${settings.asset} cannot reach this limit.`
                  ) : (
                    <>
                      A{" "}
                      <strong>
                        {percent(-scenario.threshold_shock_pct)} decline in {settings.asset}
                      </strong>{" "}
                      reaches the {money(scenario.limit_usd)} limit.{" "}
                      {scenario.can_exceed ? "A larger decline exceeds it." : "A total loss reaches the limit exactly."}
                    </>
                  )}
                </p>
                <p className="text-muted-foreground text-xs">
                  The other holding stays flat. This scenario estimates impact without assigning a probability.
                </p>
              </>
            )}
            {error && (
              <>
                <p role="alert">{error}</p>
                <Button variant="outline" onClick={reload}>
                  Retry analysis
                </Button>
              </>
            )}
            {!scenario && !error && <p role="status">Calculating scenario…</p>}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Portfolio assumptions</CardTitle>
          <CardDescription>Change the mix or replay period. Both profiles use these settings.</CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup className="grid gap-4 sm:grid-cols-3">
            <Field>
              <FieldLabel htmlFor="equity-weight">
                SPY {settings.weights.SPY}% · TLT {settings.weights.TLT}%
              </FieldLabel>
              <input
                id="equity-weight"
                aria-label="SPY allocation in percent"
                className="accent-primary w-full"
                type="range"
                min="0"
                max="100"
                value={settings.weights.SPY}
                onChange={(e) =>
                  update({ weights: { SPY: Number(e.target.value), TLT: 100 - Number(e.target.value) } })
                }
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="replay-start">Replay starts</FieldLabel>
              <Input
                type="date"
                id="replay-start"
                value={settings.start}
                onChange={(e) => update({ start: e.target.value })}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="replay-end">Replay ends</FieldLabel>
              <Input
                type="date"
                id="replay-end"
                value={settings.end}
                onChange={(e) => update({ end: e.target.value })}
              />
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>
      {result?.replay && <HistoricalReplay replay={result.replay} />}
      {result?.replay_error && (
        <Card>
          <CardHeader>
            <CardTitle>Historical replay unavailable</CardTitle>
            <CardDescription>{result.replay_error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={reload}>
              Retry historical data
            </Button>
          </CardContent>
        </Card>
      )}
      {result && <PersonaComparison settings={settings} analysis={result} persona={persona} setPersona={setPersona} />}
    </>
  );
}
