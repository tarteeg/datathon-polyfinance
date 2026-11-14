import { Skeleton } from "@/components/ui/skeleton";
import { PricePanel } from "./price-panel";

export function StockHistorySkeleton({ symbol, period }: { symbol: string; period: string }) {
  return (
    <PricePanel
      symbol={symbol}
      period={period}
      name={<Skeleton className="h-4 w-24" />}
      market={<Skeleton className="mt-1 h-3 w-20" />}
      price={<Skeleton className="h-7 w-28" />}
    >
      <div role="status" aria-label="Loading stock prices" className="flex h-72 flex-col justify-between py-3 sm:h-96">
        {[0, 1, 2, 3, 4].map((tick) => (
          <div key={tick} className="flex items-center gap-2">
            <div className="h-px flex-1 bg-border/50" />
            <Skeleton className="h-3 w-6" />
          </div>
        ))}
      </div>
    </PricePanel>
  );
}
