import { getSession } from "@/lib/session";

export async function POST(request: Request) {
  if (!(await getSession())) return new Response("Sign in to open BreakPoint AI.", { status: 401 });
  const url = new URL("/decision-lab/analyze", process.env.BACKEND_API_URL || "http://127.0.0.1:8000");
  const upstream = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
    cache: "no-store",
    signal: request.signal,
  }).catch(() => null);
  if (!upstream) return new Response("The analysis server is unavailable.", { status: 502 });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}
