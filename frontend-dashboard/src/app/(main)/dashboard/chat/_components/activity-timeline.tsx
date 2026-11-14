import { Check, ChevronDown, CircleAlert, LoaderCircle, Wrench } from "lucide-react";
import type { ChatActivity } from "@/lib/chat-stream";

const labels: Record<string, string> = {
  get_stock: "Look up stock prices",
  compare_stocks: "Compare stocks",
  discover_companies: "Find companies",
  get_my_portfolio: "Read your portfolio",
  search_news: "Search news",
};

export function ActivityTimeline({ steps, streaming }: { steps?: ChatActivity[]; streaming: boolean }) {
  if (!steps?.length) return null;
  const active = streaming && steps.find((item) => item.status === "running");
  const Icon = active ? LoaderCircle : Wrench;
  return (
    <details className="group/activity rounded-xl border bg-muted/20 text-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2">
        <Icon aria-hidden className={active ? "size-4 animate-spin" : "size-4"} />
        <span className="flex-1">
          {active
            ? (labels[active.tool] ?? active.tool)
            : `Activity · ${steps.length} tool call${steps.length === 1 ? "" : "s"}`}
        </span>
        <ChevronDown aria-hidden className="size-4 group-open/activity:rotate-180" />
      </summary>
      <ol aria-label="Tool activity" className="border-t p-3">
        {steps.map((step) => {
          const status = step.status === "running" && !streaming ? "interrupted" : step.status;
          const StatusIcon = status === "completed" ? Check : status === "running" ? LoaderCircle : CircleAlert;
          return (
            <li key={step.id} className="list-none">
              <details>
                <summary className="flex cursor-pointer items-center gap-2">
                  <StatusIcon aria-hidden className="size-4" />
                  <span className="flex-1">{labels[step.tool] ?? step.tool}</span>
                  <span className="capitalize text-muted-foreground">{status}</span>
                </summary>
                <code>{step.tool}</code>
                <pre className="text-xs">{JSON.stringify(step.input, null, 2)}</pre>
              </details>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
