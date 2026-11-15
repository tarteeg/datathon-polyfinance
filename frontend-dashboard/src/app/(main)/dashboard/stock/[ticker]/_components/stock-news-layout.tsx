"use client";

import { LayoutGrid, List } from "lucide-react";
import { type ReactNode, useState } from "react";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { setClientCookie } from "@/lib/cookie.client";

export function StockNewsLayout({
  heading,
  filters,
  initialCards,
  children,
}: {
  heading: string;
  filters?: ReactNode;
  initialCards: boolean;
  children: ReactNode;
}) {
  const [view, setView] = useState(initialCards ? "cards" : "rows");
  return (
    <section aria-labelledby="stock-news-heading" data-view={view} className="group/news @container">
      <div className={filters
        ? "mb-4 grid grid-cols-[minmax(0,1fr)_auto] items-center justify-between gap-2 border-b pb-4 sm:flex sm:flex-wrap"
        : "mb-4 flex items-center justify-between gap-2 border-b pb-4"}>
        <h2 id="stock-news-heading" className={filters ? "sr-only" : "text-lg font-medium"}>
          {heading}
        </h2>
        {filters}
        <ToggleGroup
          type="single"
          variant="outline"
          size="sm"
          spacing={0}
          aria-label="News layout"
          value={view}
          onValueChange={(next) => {
            if (!next) return;
            setView(next);
            setClientCookie("stock_news_view", next, 365);
          }}
        >
          <ToggleGroupItem value="rows">
            <List />
            <span className="sr-only sm:not-sr-only">Rows</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="cards">
            <LayoutGrid />
            <span className="sr-only sm:not-sr-only">Cards</span>
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
      {children}
    </section>
  );
}
