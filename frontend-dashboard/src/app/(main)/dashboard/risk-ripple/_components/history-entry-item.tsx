"use client";

import { ChevronDown, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { deleteHistoryEntry } from "@/server/alerts-actions";
import type { InvestigationHistoryEntry } from "@/server/riskripple";

import { ATTENTION_META, FindingsCards } from "./findings-cards";

export function HistoryEntryItem({
  entry,
  defaultOpen,
  onDeleted,
}: {
  entry: InvestigationHistoryEntry;
  defaultOpen: boolean;
  onDeleted?: (id: number) => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [deleting, setDeleting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const attention = entry.result.event_briefing
    ? ATTENTION_META[entry.result.event_briefing.attention_level] ?? ATTENTION_META.INSUFFICIENT_EVIDENCE
    : null;

  async function handleDelete() {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setDeleting(true);
    const result = await deleteHistoryEntry(entry.id);
    setDeleting(false);
    if (result.ok) onDeleted?.(entry.id);
    else setConfirming(false);
  }

  return (
    <div className="border-border flex items-start gap-2 border-b pb-4 last:border-0 last:pb-0">
      <Collapsible open={open} onOpenChange={setOpen} className="min-w-0 flex-1">
        <CollapsibleTrigger className="flex w-full flex-wrap items-center gap-2 text-left text-sm hover:underline">
          <ChevronDown className={`size-4 shrink-0 transition-transform ${open ? "" : "-rotate-90"}`} />
          <span className="text-muted-foreground text-xs">{new Date(entry.created_at).toLocaleString()}</span>
          <Badge variant="outline" className="text-xs">{entry.portfolio_holdings.join(", ")}</Badge>
          {attention && <Badge variant={attention.variant} className="text-xs">{attention.label}</Badge>}
          <span className="flex-1 truncate font-medium">{entry.event_description}</span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-3">
          <FindingsCards result={entry.result} />
        </CollapsibleContent>
      </Collapsible>
      <Button
        type="button"
        size="icon"
        variant={confirming ? "destructive" : "ghost"}
        className="shrink-0"
        disabled={deleting}
        onClick={handleDelete}
        onBlur={() => setConfirming(false)}
        title={confirming ? "Click again to confirm delete" : "Delete this investigation"}
      >
        {deleting ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
      </Button>
    </div>
  );
}
