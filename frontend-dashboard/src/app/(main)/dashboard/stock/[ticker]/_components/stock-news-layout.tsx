"use client";

import { LayoutGrid, List } from "lucide-react";
import { type ReactNode, useState } from "react";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { setClientCookie } from "@/lib/cookie.client";

export function StockNewsLayout({
  heading,
  initialCards,
  children,
}: {
  heading: string;
  initialCards: boolean;
  children: ReactNode;
}) {
  const [view, setView] = useState(initialCards ? "cards" : "rows");
  return (
    <section aria-labelledby="stock-news-heading" data-view={view} className="group/news mt-2">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="stock-news-heading" className="text-lg font-medium">
          {heading}
        </h2>
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
            Rows
          </ToggleGroupItem>
          <ToggleGroupItem value="cards">
            <LayoutGrid />
            Cards
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
      {children}
    </section>
  );
}
