import type { Metadata } from "next";

import { FinanceChat } from "./_components/finance-chat";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Finance chat", robots: { index: false, follow: false } };

export default async function Page({ searchParams }: { searchParams: Promise<{ thread?: string }> }) {
  const { user } = await requireSession();
  const { thread } = await searchParams;
  return <FinanceChat key={`${user.id}-${thread ?? "latest"}`} requestedThread={thread} />;
}
