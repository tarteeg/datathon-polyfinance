import type { MetadataRoute } from "next";

import { APP_CONFIG } from "@/config/app-config";

const PUBLIC_ROUTES = [
  "/dashboard/home",
  "/auth/v1/login",
  "/auth/v1/register",
  "/dashboard/chat",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_ROUTES.map((route) => ({
    url: `${APP_CONFIG.url}${route}`,
  }));
}
