import type { ReactNode } from "react";

import { redirect } from "next/navigation";

import { getSession } from "@/lib/session";

export default async function AuthLayout({ children }: Readonly<{ children: ReactNode }>) {
  if (await getSession()) redirect("/dashboard/home");
  return children;
}
