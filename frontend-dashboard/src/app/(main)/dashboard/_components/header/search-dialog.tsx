"use client";

import * as React from "react";

import { useRouter } from "next/navigation";

import { defaultFilter } from "cmdk";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import { sp500 } from "@/data/sp500";
import type { NavMainItem } from "@/navigation/sidebar/sidebar-items";
import { sidebarItems } from "@/navigation/sidebar/sidebar-items";

type SearchItem = {
  id: string;
  group: string;
  label: string;
  url: string;
  icon?: NavMainItem["icon"];
  disabled?: boolean;
  newTab?: boolean;
};

const sidebarGroupLabels = new Set(sidebarItems.flatMap((group) => (group.label ? [group.label] : [])));

function getSubItemGroup(groupLabel: string | undefined, itemTitle: string) {
  return sidebarGroupLabels.has(itemTitle) ? (groupLabel ?? "Other") : itemTitle;
}

const searchItems: SearchItem[] = sidebarItems.flatMap((group) =>
  group.items.flatMap((item) => {
    if (item.subItems) {
      return item.subItems.map((sub) => ({
        id: sub.id,
        group: getSubItemGroup(group.label, item.title),
        label: sub.title,
        url: sub.url,
        icon: item.icon,
        disabled: sub.disabled,
        newTab: sub.newTab,
      }));
    }
    return [
      {
        id: item.id,
        group: group.label ?? "Other",
        label: item.title,
        url: item.url,
        icon: item.icon,
        disabled: item.disabled,
        newTab: item.newTab,
      },
    ];
  }),
);

function getAvailableItems(items: SearchItem[]) {
  return items.filter((item) => !item.disabled && !item.url.includes("coming-soon"));
}

const recommendations = getAvailableItems(searchItems);

const stocks = Object.entries(sp500);

function stockScore(symbol: string, name: string, query: string) {
  const term = query.trim().toLowerCase();
  if (!term) return 0;
  if (symbol.toLowerCase() === term) return 1;
  if (symbol.toLowerCase().startsWith(term)) return 0.9;
  if (name.toLowerCase().startsWith(term)) return 0.8;
  return name.toLowerCase().includes(term) ? 0.7 : 0;
}

function commandFilter(value: string, query: string, keywords?: string[]) {
  if (value.startsWith("stock:")) {
    const symbol = value.slice(6);
    return query.trim() ? stockScore(symbol, sp500[symbol] ?? symbol, query) : 1;
  }
  return defaultFilter(value, query, keywords);
}

function groupBy(items: SearchItem[]) {
  const groups = [...new Set(items.map((item) => item.group))];
  return groups.map((group) => ({
    group,
    items: items.filter((item) => item.group === group),
  }));
}

export function SearchDialog({
  stocksOnly = false,
  portfolioTickers = [],
}: { stocksOnly?: boolean; portfolioTickers?: readonly string[] }) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const router = useRouter();
  const stockMatches = query.trim()
    ? stocks
        .map(([symbol, name]) => ({ symbol, name, score: stockScore(symbol, name, query) }))
        .filter((stock) => stock.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 5)
    : portfolioTickers.map((symbol) => ({ symbol, name: sp500[symbol] ?? symbol }));

  React.useEffect(() => {
    if (stocksOnly) return;
    const down = (e: KeyboardEvent) => {
      if (e.key === "j" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [stocksOnly]);

  const handleOpenChange = (value: boolean) => {
    setOpen(value);
    if (!value) setQuery("");
  };

  const handleSelect = (item: SearchItem) => {
    if (item.disabled) return;
    handleOpenChange(false);
    if (item.newTab) {
      window.open(item.url, "_blank", "noopener,noreferrer");
    } else {
      router.push(item.url);
    }
  };

  const renderGroups = (items: SearchItem[]) =>
    groupBy(items).map(({ group, items: groupItems }, index) => (
      <React.Fragment key={group}>
        {index > 0 && <CommandSeparator />}
        <CommandGroup heading={group}>
          {groupItems.map((item) => (
            <CommandItem
              disabled={item.disabled}
              key={`${group}-${item.id}`}
              value={`${item.group} ${item.label}`}
              onSelect={() => handleSelect(item)}
            >
              <span className="flex min-w-0 items-center gap-2">
                {item.icon && <item.icon />}
                <span className="truncate">{item.label}</span>
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      </React.Fragment>
    ));

  return (
    <>
      {stocksOnly ? (
        <SidebarMenuButton tooltip="Search stock" onClick={() => handleOpenChange(true)}>
          <Search />
          <span>Search stock</span>
        </SidebarMenuButton>
      ) : (
        <Button
          onClick={() => handleOpenChange(true)}
          variant="link"
          className="text-muted-foreground px-0! font-normal hover:no-underline"
        >
          <Search data-icon="inline-start" />
          Search
          <kbd className="bg-muted inline-flex h-5 items-center gap-1 rounded border px-1.5 text-[10px] font-medium select-none">
            <span className="text-xs">⌘</span>J
          </kbd>
        </Button>
      )}
      <CommandDialog
        title={stocksOnly ? "Search stock" : "Search dashboard"}
        open={open}
        onOpenChange={handleOpenChange}
      >
        <Command filter={commandFilter}>
          <CommandInput
            placeholder={stocksOnly ? "Search symbol or company…" : "Search pages, stock symbols, or companies…"}
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            <CommandEmpty>
              {stocksOnly && !query.trim() ? "Type a ticker or company name." : "No results found."}
            </CommandEmpty>
            {!stocksOnly && renderGroups(query ? searchItems : recommendations)}
            {stockMatches.length > 0 && (
              <CommandGroup heading={query.trim() ? "Stocks" : "Your portfolio"}>
                {stockMatches.map(({ symbol, name }) => (
                  <CommandItem
                    key={symbol}
                    value={`stock:${symbol}`}
                    onSelect={() => {
                      handleOpenChange(false);
                      router.push(`/dashboard/stock/${encodeURIComponent(symbol)}`);
                    }}
                  >
                    <span>{symbol}</span>
                    <span className="truncate text-muted-foreground">{name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
