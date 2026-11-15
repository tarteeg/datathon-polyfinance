"use client";

import { MessageSquareText } from "lucide-react";
import { useActionState } from "react";
import { Button } from "@/components/ui/button";

export function ExplainChartButton({ explain }: { explain: () => Promise<string> }) {
  const [error, action, pending] = useActionState(explain, "");
  return (
    <form action={action} className="flex flex-wrap items-center gap-2">
      <Button type="submit" size="sm" variant="outline" disabled={pending}>
        <MessageSquareText aria-hidden />
        {pending ? "Explaining chart…" : "Explain this chart"}
      </Button>
      {error && (
        <span role="alert" className="text-sm text-destructive">
          {error}
        </span>
      )}
    </form>
  );
}
