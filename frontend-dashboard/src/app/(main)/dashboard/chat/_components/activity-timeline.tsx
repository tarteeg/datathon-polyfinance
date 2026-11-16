import { Check, ChevronDown, CircleAlert, LoaderCircle, ShieldCheck, Wrench } from "lucide-react";

import type { ChatActivity, FigureCheck } from "@/lib/chat-stream";

const labels: Record<string, string> = {
  analyze_breakpoint: "Replay portfolio and test the loss limit",
  get_stock: "Look up stock prices",
  compare_stocks: "Compare stocks",
  discover_companies: "Find companies",
  get_my_portfolio: "Read your portfolio",
  search_news: "Search news",
  simulate_transfer: "Simulate a transfer",
  sector_exposure: "Measure sector exposure",
  concentration: "Measure concentration",
  risk_history: "Measure historical risk",
  check_data: "Check data coverage",
  convert_currency: "Convert currency",
  verify_answer: "Check figures",
};

const verdicts: Record<FigureCheck["code"], string> = {
  verified: "Figures found in sources",
  review: "Needs review",
  rejected: "Figures without a source",
  unverified: "Not checked",
};

const rules: Record<NonNullable<FigureCheck["findings"]>[number]["rule"], string> = {
  causal_claim: "Cause not established by the data",
  advice: "Reads as advice",
  unreported_gap: "Data gap not mentioned",
  mismatched_series: "Series compared without saying they differ",
};

const VERIFY = "verify_answer";

// "simulate_transfer · AlphaForge calculation.concentration.before.herfindahl" becomes "concentration.before.herfindahl".
const shortSource = (source: string) => (source.split(" · ").pop() ?? source).split(".").slice(-3).join(".");

function FigureCheckDetails({ check }: { check: FigureCheck }) {
  return (
    <div className="space-y-2 py-1 text-xs">
      <p>
        {check.checked} figure{check.checked === 1 ? "" : "s"} checked against tool results, your question and saved
        data.
      </p>
      {check.unmatched.length > 0 && (
        <div>
          <p className="font-medium">No source found</p>
          <ul className="list-inside list-disc">
            {check.unmatched.map((item) => (
              <li key={`${item.location}-${item.text}`}>
                <code>{item.text}</code> in {item.location}
                {item.status === "weak_unmatched" ? " (small whole number)" : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
      {check.findings && check.findings.length > 0 && (
        <div>
          <p className="font-medium">Statements to review</p>
          <ul className="list-inside list-disc">
            {check.findings.map((item) => (
              <li key={`${item.rule}-${item.quote}`}>
                {rules[item.rule]}: <q>{item.quote}</q>. {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      {check.judge === "unavailable" && <p className="text-muted-foreground">The statement review was unavailable.</p>}
      {check.derived.length > 0 && (
        <div>
          <p className="font-medium">Computed from other figures, not returned by a tool</p>
          <ul className="list-inside list-disc">
            {check.derived.map((item) => (
              <li key={`${item.location}-${item.text}`}>
                <code>{item.text}</code> in {item.location}
                {item.operands[0] ? `, from ${item.operands[0].map(shortSource).join(" and ")}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function ActivityTimeline({ steps, streaming }: { steps?: ChatActivity[]; streaming: boolean }) {
  if (!steps?.length) return null;
  const tools = steps.filter((item) => item.tool !== VERIFY);
  const check = steps.find((item) => item.tool === VERIFY)?.output;
  const active = streaming && steps.find((item) => item.status === "running");
  let Icon = Wrench;
  if (active) Icon = LoaderCircle;
  else if (check && !tools.length) Icon = ShieldCheck;
  const toolSummary = `Activity · ${tools.length} tool call${tools.length === 1 ? "" : "s"}`;
  return (
    <details className="group/activity rounded-xl border bg-muted/20 text-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2">
        <Icon aria-hidden className={active ? "size-4 animate-spin" : "size-4"} />
        <span className="flex-1">
          {active
            ? (labels[active.tool] ?? active.tool)
            : [tools.length ? toolSummary : "Activity", check && verdicts[check.code]].filter(Boolean).join(" · ")}
        </span>
        <ChevronDown aria-hidden className="size-4 group-open/activity:rotate-180" />
      </summary>
      <ol aria-label="Tool activity" className="border-t p-3">
        {steps.map((step) => {
          const status = step.status === "running" && !streaming ? "interrupted" : step.status;
          const StatusIcon = status === "completed" ? Check : status === "running" ? LoaderCircle : CircleAlert;
          const result = step.tool === VERIFY ? step.output : undefined;
          return (
            <li key={step.id} className="list-none">
              <details>
                <summary className="flex cursor-pointer items-center gap-2">
                  <StatusIcon aria-hidden className="size-4" />
                  <span className="flex-1">{labels[step.tool] ?? step.tool}</span>
                  {result ? (
                    <span className="text-muted-foreground">{verdicts[result.code]}</span>
                  ) : (
                    <span className="capitalize text-muted-foreground">{status}</span>
                  )}
                </summary>
                {result ? (
                  <FigureCheckDetails check={result} />
                ) : (
                  <>
                    <code>{step.tool}</code>
                    <pre className="overflow-x-auto text-xs">{JSON.stringify(step.input, null, 2)}</pre>
                    {step.result && <pre className="overflow-x-auto text-xs">{JSON.stringify(step.result, null, 2)}</pre>}
                  </>
                )}
              </details>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
