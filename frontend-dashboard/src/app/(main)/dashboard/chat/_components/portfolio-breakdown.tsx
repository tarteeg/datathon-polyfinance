import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export type PortfolioSnapshot = {
  view: "holdings" | "valuation" | "news";
  retrieved: string;
  positions: {
    ticker: string;
    quantity: number;
    currency?: string;
    value?: number;
    dailyChange?: number;
    weightPercent?: number;
    asOf?: string;
  }[];
  watchlist: string[];
  totals: Record<string, { value: number; dailyChange: number | null }>;
};

const amount = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
function money(value: number | undefined | null, currency?: string) {
  return value == null || !currency ? "Unavailable" : `${amount.format(value)} ${currency}`;
}

export function PortfolioBreakdown({ snapshot }: { snapshot: PortfolioSnapshot }) {
  if (snapshot.view !== "valuation" || !snapshot.positions.length) return null;
  return (
    <section aria-label="Portfolio breakdown" className="flex flex-col gap-2">
      {Object.entries(snapshot.totals).map(([currency, total]) => (
        <p key={currency}>
          <strong>{money(total.value, currency)}</strong> in priced positions · Daily change:{" "}
          {money(total.dailyChange, currency)}
        </p>
      ))}
      <Table>
        <TableHeader>
          <TableRow>
            {["Holding", "Shares", "Value", "Daily change", "Weight¹"].map((label) => (
              <TableHead key={label}>{label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {snapshot.positions.map((p) => (
            <TableRow key={p.ticker}>
              <TableCell>{p.ticker}</TableCell>
              <TableCell>{p.quantity}</TableCell>
              <TableCell>{money(p.value, p.currency)}</TableCell>
              <TableCell>{money(p.dailyChange, p.currency)}</TableCell>
              <TableCell>{p.weightPercent == null ? "Unavailable" : `${amount.format(p.weightPercent)}%`}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <p className="text-xs text-muted-foreground">
        ¹ Share of priced positions in the same currency. Yahoo Finance regular-session quotes, retrieved{" "}
        {new Date(snapshot.retrieved).toUTCString()}.
      </p>
      {snapshot.watchlist.length > 0 && (
        <p className="text-sm">Tracked without a share count: {snapshot.watchlist.join(", ")}.</p>
      )}
    </section>
  );
}
