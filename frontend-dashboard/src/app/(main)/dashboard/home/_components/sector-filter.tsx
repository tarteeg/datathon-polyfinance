"use client";

import { useRouter } from "next/navigation";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";

export function SectorFilter({ sector, sectors }: { sector?: string; sectors: string[] }) {
  const router = useRouter();
  return (
    <NativeSelect
      aria-label="Filter stocks by sector"
      value={sector || ""}
      onChange={(event) => {
        const value = event.target.value;
        router.push(value ? `/dashboard/home?sector=${encodeURIComponent(value)}` : "/dashboard/home", {
          scroll: false,
        });
      }}
    >
      <NativeSelectOption value="">All sectors</NativeSelectOption>
      {sectors.map((name) => (
        <NativeSelectOption key={name} value={name}>
          {name}
        </NativeSelectOption>
      ))}
    </NativeSelect>
  );
}
