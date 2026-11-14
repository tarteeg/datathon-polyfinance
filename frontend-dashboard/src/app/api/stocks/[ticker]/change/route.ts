import { getSession } from "@/lib/session";
import { fetchHistory } from "@/server/stock-history";

export async function GET(_request: Request, { params }: { params: Promise<{ ticker: string }> }) {
  if (!(await getSession())) return new Response(null, { status: 401 });
  const { ticker } = await params;
  const history = await fetchHistory(ticker, "1d").catch(() => null);
  if (!history) return new Response(null, { status: 204 });
  const { regularMarketPrice, previousClose, currency } = history.ticker;
  if (previousClose == null) return new Response(null, { status: 204 });
  return Response.json(
    { change: Number((regularMarketPrice - previousClose).toFixed(4)), currency },
    { headers: { "Cache-Control": "private, max-age=60" } },
  );
}
