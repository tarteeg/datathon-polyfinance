import { Activity as ActivityIcon, Check, History, LoaderCircle, TriangleAlert } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trace, TraceIcon, TraceLine, TraceTitle } from "@/components/ui/trace";
import type { EventResult } from "./event-findings";

type Step = {
  key: string;
  title: string;
  detail: string;
  status: "running" | "completed" | "reused" | "unavailable";
  updated: string;
  done?: number | null;
  total?: number | null;
};
export type Activity = {
  id: string;
  steps: Step[];
  partial: EventResult[];
  first_finding_ms: number | null;
  elapsed_ms: number;
  model_calls: number;
};

const icons = { completed: Check, running: LoaderCircle, reused: History, unavailable: TriangleAlert };
export const clockTime = (value: string) =>
  new Date(value).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
function duration(ms: number) {
  if (ms < 1000) return `${ms} ms`;
  const seconds = Math.round(ms / 1000);
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export function ScanActivity({ activity, running }: { activity: Activity; running: boolean }) {
  const steps = [...activity.steps].sort((a, b) => b.updated.localeCompare(a.updated));
  const active = steps.find((step) => step.status === "running");
  const latest = running ? (active ?? steps[0]) : steps[0];
  return (
    <Card className="h-fit min-w-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ActivityIcon className="size-4" aria-hidden="true" />
          Investigation activity
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 has-[details[open]]:[&>dl]:grid">
        <div role="status" className="flex flex-col gap-1 rounded-lg bg-muted px-3 py-3 text-sm">
          <span className="text-xs text-muted-foreground">{running ? "Current step" : "Last step"}</span>
          <strong>{latest?.title ?? "Preparing investigation"}</strong>
          {latest?.detail && <p className="text-pretty leading-snug text-muted-foreground">{latest.detail}</p>}
          {latest?.total != null && latest.total > 0 && (
            <p className="font-mono text-xs">
              {latest.done?.toLocaleString()} / {latest.total.toLocaleString()}
            </p>
          )}
        </div>
        <dl className="hidden gap-2 text-xs @min-[52rem]:grid">
          {activity.first_finding_ms != null && (
            <div className="flex justify-between">
              <dt>First verified finding</dt>
              <dd className="font-mono">{duration(activity.first_finding_ms)}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt>Elapsed at last update</dt>
            <dd className="font-mono">{duration(activity.elapsed_ms)}</dd>
          </div>
          <div className="flex justify-between">
            <dt>Bedrock calls</dt>
            <dd className="font-mono">{activity.model_calls}</dd>
          </div>
        </dl>
        <details className="border-t pt-3">
          <summary className="cursor-pointer rounded-sm text-sm font-medium">Step history ({steps.length})</summary>
          <Trace className="mt-3 max-h-80 overflow-y-auto overscroll-contain pr-2">
            {steps.map((step) => {
              const Icon = icons[step.status];
              return (
                <div className="flex-col border-l pl-3 pb-2" key={step.key}>
                  <TraceLine>
                    <TraceIcon>
                      <Icon />
                    </TraceIcon>
                    <TraceTitle className="whitespace-normal font-medium text-foreground">{step.title}</TraceTitle>
                  </TraceLine>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{step.detail}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    <span className="capitalize">{step.status}</span> ·{" "}
                    <time dateTime={step.updated}>{clockTime(step.updated)}</time>
                    {step.total != null && ` · ${step.done} / ${step.total}`}
                  </p>
                </div>
              );
            })}
          </Trace>
        </details>
      </CardContent>
    </Card>
  );
}
