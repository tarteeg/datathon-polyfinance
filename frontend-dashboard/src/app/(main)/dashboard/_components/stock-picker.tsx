"use client";

import { ChevronsUpDown } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { sp500 } from "@/data/sp500";

const allSymbols = Object.keys(sp500);

export function StockPicker({
  id,
  ticker,
  onSelect,
  symbols = allSymbols,
  disabled,
  filter = false,
}: {
  id?: string;
  ticker: string;
  onSelect: (ticker: string) => void;
  symbols?: string[];
  disabled?: boolean;
  filter?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const typed = query.trim().toUpperCase();
  const custom =
    filter && symbols === allSymbols && /^[A-Z0-9^][A-Z0-9.^=-]{0,19}$/.test(typed) && !allSymbols.includes(typed);

  function select(value: string) {
    onSelect(value);
    setOpen(false);
  }
  return (
    <Popover
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        setQuery("");
      }}
      modal
    >
      <PopoverTrigger asChild>
        <Button id={id} type="button" variant="outline" className="w-full justify-between" disabled={disabled}>
          <span className="truncate">
            {ticker
              ? [ticker, sp500[ticker]].filter(Boolean).join(" — ")
              : filter
                ? "Filter by ticker"
                : "Select a stock"}
          </span>
          <ChevronsUpDown className="text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" aria-label="Choose a stock" className="w-(--radix-popover-trigger-width) p-0">
        <Command label="Stock suggestions">
          <CommandInput
            aria-label="Search stocks"
            placeholder="Search symbol or company…"
            value={query}
            onValueChange={setQuery}
          />
          <CommandList className="max-h-56">
            <CommandEmpty>No matching stocks.</CommandEmpty>
            <CommandGroup>
              {filter && (
                <CommandItem value="Any ticker" data-checked={!ticker} onSelect={() => select("")}>
                  Any ticker
                </CommandItem>
              )}
              {symbols.map((symbol) => (
                <CommandItem
                  key={symbol}
                  value={symbol}
                  keywords={[sp500[symbol] ?? ""]}
                  data-checked={ticker === symbol}
                  onSelect={() => select(symbol)}
                >
                  <span className="w-14 shrink-0 font-medium">{symbol}</span>
                  <span className="truncate text-muted-foreground">{sp500[symbol]}</span>
                </CommandItem>
              ))}
              {custom && (
                <CommandItem value={typed} onSelect={() => select(typed)}>
                  Use ticker {typed}
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
