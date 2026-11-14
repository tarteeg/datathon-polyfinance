import "server-only";

import { cache } from "react";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { auth } from "@/lib/auth";

export const getSession = cache(async () =>
  auth.api.getSession({
    headers: await headers(),
    query: { disableRefresh: true },
  }),
);

// Call at each protected data/action boundary; a layout alone is not authorization.
export async function requireSession() {
  const session = await getSession();
  if (!session) redirect("/auth/v1/login");
  return session;
}
