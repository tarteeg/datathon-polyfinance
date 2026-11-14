"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/button";

export function ExplainChartButton({ explain }: { explain: () => Promise<string> }) {
  const [error, action, pending] = useActionState(explain, "");
  return (
    <form action={action} className="mt-3 flex items-center gap-3">
      <Button type="submit" variant="outline" disabled={pending}>
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
