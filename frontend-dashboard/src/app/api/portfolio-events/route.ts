import { getSession } from "@/lib/session";
import { getHoldings } from "@/server/portfolio";

async function requestScan(action: "status" | "scan") {
  const session = await getSession();
  if (!session) return Response.json({ error: "Sign in to scan your portfolio." }, { status: 401 });
  const holdings = Object.fromEntries(
    (await getHoldings()).map(({ ticker, quantity }) => [ticker, quantity === null ? null : Number(quantity)]),
  );
  try {
    const response = await fetch(
      new URL(`/riskripple/events/${action}`, process.env.BACKEND_API_URL || "http://127.0.0.1:8000"),
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Chat-Key": process.env.CHAT_API_KEY ?? "" },
        body: JSON.stringify({ user_id: session.user.id, holdings, persona: session.user.investorPersona }),
        cache: "no-store",
        signal: AbortSignal.timeout(25000),
      },
    );
    if (!response.ok) return Response.json({ error: "The portfolio scan service is unavailable." }, { status: 502 });
    return Response.json(await response.json(), { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return Response.json({ error: "Could not reach the portfolio scan service." }, { status: 502 });
  }
}

export function GET() {
  return requestScan("status");
}

export function POST() {
  return requestScan("scan");
}
