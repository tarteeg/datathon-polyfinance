import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { AddStockDialog } from "../_components/sidebar/add-stock-dialog";
import { Discover } from "./_components/discover";
import { Portfolio } from "./_components/portfolio";

export default async function HomePage({ searchParams }: { searchParams: Promise<{ sector?: string }> }) {
  const { sector } = await searchParams;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-3xl tracking-tight">Portfolio and market activity</h1>
      <div>
        <AddStockDialog sidebar={false} />
      </div>
      <Suspense fallback={<Skeleton className="h-32" role="status" aria-label="Loading portfolio" />}>
        <Portfolio />
      </Suspense>
      <div className="mt-6 min-w-0 border-t pt-7">
        <Suspense fallback={<Skeleton className="h-64" role="status" aria-label="Loading rankings" />}>
          <Discover sector={sector} />
        </Suspense>
      </div>
    </div>
  );
}
