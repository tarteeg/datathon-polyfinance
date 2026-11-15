import type { Metadata } from "next";

import { DecisionLab } from "./_components/decision-lab";

export const metadata: Metadata = { title: "BreakPoint AI", robots: { index: false, follow: false } };

export default function Page() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">BreakPoint AI</h1>
        <p className="text-muted-foreground">
          How far can one holding fall before your portfolio crosses its loss limit?
        </p>
      </header>
      <DecisionLab />
    </main>
  );
}
