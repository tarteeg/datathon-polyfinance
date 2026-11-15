import { useEffect, useRef, useState } from "react";

import { useRouter } from "next/navigation";

import { ActivityTimeline } from "@/app/(main)/dashboard/chat/_components/activity-timeline";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { type ChatActivity, readChatStream } from "@/lib/chat-stream";

import { type Analysis, type Persona, percent, type Settings, statusLabel } from "./types";

const profiles = {
  Robert: [
    "3–5 years · Capital preservation",
    "A decline leaves less time to rebuild capital before withdrawals. The replay can show the depth of a past loss, but it cannot promise a recovery date.",
  ],
  Amira: [
    "15+ years · Growth and diversification",
    "A longer horizon gives more time to absorb losses. The single-fund shock shows how much risk one holding can still contribute to a diversified portfolio.",
  ],
  Mateo: [
    "8–12 years · Balanced growth and ESG",
    "Compare the loss with the stability needed over this horizon. These price histories contain no evidence for judging either fund’s ESG characteristics.",
  ],
};

export function PersonaComparison({
  settings,
  analysis,
  persona,
  setPersona,
}: {
  settings: Settings;
  analysis: Analysis;
  persona: Persona;
  setPersona: (name: Persona) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState<ChatActivity[]>([]);
  const [error, setError] = useState("");
  const router = useRouter();
  const explanation = useRef<AbortController | null>(null);
  useEffect(() => () => explanation.current?.abort(), []);

  async function explain() {
    const controller = new AbortController();
    explanation.current = controller;
    const threadId = crypto.randomUUID();
    setBusy(true);
    setError("");
    setSteps([]);
    const q = settings;
    const question = `Did this fictional portfolio cross its ${q.loss_limit_pct}% peak-to-trough loss limit between ${q.start} and ${q.end}? Explain for ${persona}. Compare with an instantaneous ${q.shock_pct}% ${q.asset} shock, holding the other ETF flat. Portfolio: USD ${q.principal}, daily-rebalanced ${q.weights.SPY}% SPY and ${q.weights.TLT}% TLT.`;
    try {
      const response = await fetch("/api/finance-chat", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ threadId, question, lastTurn: 0, decisionLab: { ...q, persona } }),
      });
      if (!response.ok) throw new Error("The finance assistant is unavailable.");
      for await (const event of readChatStream(response)) {
        if (controller.signal.aborted) return;
        if (event.error) throw new Error(event.error);
        if (event.activity) setSteps((old) => [...old.filter((step) => step.id !== event.activity.id), event.activity]);
        if (event.done) {
          window.dispatchEvent(new Event("finance-chat-saved"));
          router.push(`/dashboard/chat?thread=${threadId}`);
          return;
        }
      }
      throw new Error("The explanation was interrupted.");
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError(cause instanceof Error ? cause.message : "Could not open the explanation.");
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Same loss, different horizons</CardTitle>
        <CardDescription>
          {statusLabel[analysis.scenario.status]} · Both profiles use the same {percent(settings.loss_limit_pct)} loss
          limit and the same {percent(analysis.scenario.impact_pct)} simulated move.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          {([persona === "Mateo" ? "Mateo" : "Robert", "Amira"] as const).map((name) => (
            <div key={name} className="rounded-lg border p-4">
              <h3 className="font-semibold">{name}</h3>
              <p className="text-muted-foreground mb-2 text-xs">{profiles[name][0]}</p>
              <p>{profiles[name][1]}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="lab-persona">Explain for</label>
          <NativeSelect
            id="lab-persona"
            value={persona}
            disabled={busy}
            onChange={(e) => setPersona(e.target.value as Persona)}
          >
            {Object.keys(profiles).map((name) => (
              <NativeSelectOption key={name}>{name}</NativeSelectOption>
            ))}
          </NativeSelect>
          <Button onClick={explain} disabled={busy}>
            {busy ? "Checking the replay…" : "Explain in Finance chat"}
          </Button>
        </div>
        <ActivityTimeline steps={steps} streaming={busy} />
        {error && <p role="alert">{error}</p>}
      </CardContent>
    </Card>
  );
}
