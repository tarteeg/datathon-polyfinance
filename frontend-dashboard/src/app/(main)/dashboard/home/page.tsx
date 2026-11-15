import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { AddStockDialog } from "../_components/sidebar/add-stock-dialog";
import { Discover } from "./_components/discover";
import { Portfolio } from "./_components/portfolio";

export default async function HomePage({ searchParams }: { searchParams: Promise<{ sector?: string }> }) {
  const { sector } = await searchParams;
  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Portfolio overview</h1>
        <AddStockDialog sidebar={false} />
      </header>
      <Suspense fallback={<Skeleton className="h-32" role="status" aria-label="Loading portfolio" />}>
        <Portfolio />
      </Suspense>
      <div className="min-w-0">
        <Suspense fallback={<Skeleton className="h-64" role="status" aria-label="Loading rankings" />}>
          <Discover sector={sector} />
        </Suspense>
      </div>
    </div>
  );
}
