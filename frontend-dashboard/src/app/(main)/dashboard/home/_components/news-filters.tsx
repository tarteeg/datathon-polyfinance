"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { StockPicker } from "../../_components/stock-picker";

export function NewsFilters({ all, ticker, saved }: { all: boolean; ticker: string; saved: string[] }) {
  const [scope, setScope] = useState(all ? "all" : "portfolio");
  const [symbol, setSymbol] = useState(ticker);
  return (
    <form action="/dashboard/home" className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="tab" value="news" />
      <input type="hidden" name="symbol" value={symbol} />
      <NativeSelect
        name="scope"
        aria-label="News scope"
        value={scope}
        onChange={(event) => {
          const next = event.target.value;
          setScope(next);
          if (next === "portfolio" && !saved.includes(symbol)) setSymbol("");
        }}
      >
        <NativeSelectOption value="portfolio">My portfolio</NativeSelectOption>
        <NativeSelectOption value="all">All symbols</NativeSelectOption>
      </NativeSelect>
      <div className="w-60 max-w-full">
        <StockPicker filter ticker={symbol} symbols={scope === "all" ? undefined : saved} onSelect={setSymbol} />
      </div>
      <Button size="sm" variant="outline" type="submit">
        Apply
      </Button>
    </form>
  );
}
