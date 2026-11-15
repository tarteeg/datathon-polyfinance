import { redirect } from "next/navigation";

// This page split into two: /dashboard/risk-ripple/news and
// /dashboard/risk-ripple/investigations, each with its own sidebar entry.
export default function Page() {
  redirect("/dashboard/risk-ripple/news");
}
