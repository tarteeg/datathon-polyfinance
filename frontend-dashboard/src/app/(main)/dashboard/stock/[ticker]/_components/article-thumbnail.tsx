"use client";

import Image from "next/image";
import { useState } from "react";

import { ItemMedia } from "@/components/ui/item";

export function ArticleThumbnail({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  if (failed || !/^https?:\/\//i.test(src)) return null;

  return (
    <ItemMedia
      variant="image"
      className="h-14 w-16 sm:h-20 sm:w-28 group-data-[view=cards]/news:h-40 group-data-[view=cards]/news:w-full group-data-[view=cards]/news:rounded-none group-data-[view=cards]/news:translate-y-0"
    >
      <Image
        src={src}
        alt=""
        width={480}
        height={270}
        unoptimized
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
      />
    </ItemMedia>
  );
}
