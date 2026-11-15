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
      className="h-16 w-24 group-data-[view=cards]/news:aspect-video group-data-[view=cards]/news:h-auto group-data-[view=cards]/news:w-full"
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
