"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function SectorTabs({ sector, sectors, children }: { sector?: string; sectors: string[]; children: ReactNode }) {
  const router = useRouter();
  const selected = sector || "all";

  return (
    <Tabs
      value={selected}
      activationMode="manual"
      onValueChange={(value) => {
        router.push(value === "all" ? "/dashboard/home" : `?sector=${encodeURIComponent(value)}`, { scroll: false });
      }}
    >
      <div className="min-w-0 overflow-x-auto border-b pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <TabsList variant="line" aria-label="Filter stocks by sector">
          <TabsTrigger value="all">All sectors</TabsTrigger>
          {sectors.map((name) => (
            <TabsTrigger key={name} value={name}>{name}</TabsTrigger>
          ))}
        </TabsList>
      </div>
      <TabsContent value={selected}>{children}</TabsContent>
    </Tabs>
  );
}
