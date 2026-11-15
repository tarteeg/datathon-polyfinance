"use client";

import { ChevronDown, ExternalLink, Loader2, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { type AlertCard, runAlertsScan } from "@/server/alerts-actions";

function AlertRow({ alert }: { alert: AlertCard }) {
  return (
    <div className="flex flex-col gap-1 border-border border-b py-3 last:border-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{alert.symbol}</Badge>
        <Badge variant="outline" className="text-xs">
          {alert.source === "news" ? "News" : "Regulatory"}
        </Badge>
        {alert.documentUrl ? (
          <a
            href={alert.documentUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-sm font-medium hover:underline"
          >
            {alert.title || "Source"}
            <ExternalLink className="size-3.5" />
          </a>
        ) : (
          <span className="text-sm font-medium">{alert.title}</span>
        )}
      </div>
      {alert.recommendation && <p className="text-muted-foreground text-sm">{alert.recommendation}</p>}
    </div>
  );
}

export function AlertsPanel() {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "done"; confirmed: AlertCard[]; hypotheses: AlertCard[]; tickers: string[] }
  >({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    runAlertsScan().then((result) => {
      if (cancelled) return;
      if (!result.ok) setState({ status: "error", message: result.error });
      else setState({ status: "done", confirmed: result.confirmed, hypotheses: result.hypotheses, tickers: result.tickers });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="size-4" />
          Portfolio alerts
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {state.status === "loading" && (
          <div className="text-muted-foreground flex items-center gap-2 text-sm">
            <Loader2 className="size-4 animate-spin" />
            Checking real regulatory and news sources against your portfolio…
          </div>
        )}

        {state.status === "error" && <p className="text-destructive text-sm">{state.message}</p>}

        {state.status === "done" && state.tickers.length === 0 && (
          <p className="text-muted-foreground text-sm">Add a stock to your portfolio to start getting alerts.</p>
        )}

        {state.status === "done" && state.tickers.length > 0 && state.confirmed.length === 0 && (
          <p className="text-muted-foreground text-sm">
            No confirmed alerts for {state.tickers.join(", ")} right now — checked real Federal Register documents
            and real recent news against your actual holdings.
          </p>
        )}

        {state.status === "done" && state.confirmed.length > 0 && (
          <div className="flex flex-col">
            {state.confirmed.map((a) => (
              <AlertRow key={a.key} alert={a} />
            ))}
          </div>
        )}

        {state.status === "done" && state.hypotheses.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-xs hover:underline">
              <ChevronDown className="size-3.5" />
              {state.hypotheses.length} unconfirmed possible connection{state.hypotheses.length === 1 ? "" : "s"} (thin
              evidence, not shown as alerts)
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 flex flex-col">
              {state.hypotheses.map((a) => (
                <AlertRow key={a.key} alert={a} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}
