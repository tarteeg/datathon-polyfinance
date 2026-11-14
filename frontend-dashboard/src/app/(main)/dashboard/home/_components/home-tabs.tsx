"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function HomeTabs({ tab, children }: { tab: string; children: ReactNode }) {
  const router = useRouter();
  return (
    <Tabs
      value={tab}
      onValueChange={(value) => router.push(value === "portfolio" ? "/dashboard/home" : `?tab=${value}`, { scroll: false })}
    >
      <TabsList variant="line">
        <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
        <TabsTrigger value="news">News</TabsTrigger>
      </TabsList>
      <TabsContent value={tab} key={tab} className="pt-4">
        {children}
      </TabsContent>
    </Tabs>
  );
}
