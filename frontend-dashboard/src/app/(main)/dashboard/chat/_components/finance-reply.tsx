import { PortfolioBreakdown, type PortfolioSnapshot } from "./portfolio-breakdown";
import { createLibrary, defineComponent, Renderer } from "@openuidev/react-lang";
import { createContext, useContext } from "react";
import type { StockPlot, StockSnapshot } from "../actions";
import { StockPriceChart } from "../../_components/stock-price-chart";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { z } from "zod";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const label = z.string().trim().min(1);
const columns = z.tuple([label, label, label]);
const rows = z.array(columns).min(1).max(8);
function ReplyTable({ title, headers, data }: { title: string; headers: string[]; data: string[][] }) {
  return (
    <Table>
      <TableCaption className="sr-only">{title}</TableCaption>
      <TableHeader>
        <TableRow>
          {headers.map((header, i) => (
            <TableHead key={i} scope="col" className="whitespace-normal">
              {header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, i) => (
          <TableRow key={i}>
            {row.map((cell, j) => (
              <TableCell key={j} className="whitespace-normal align-top tabular-nums">
                {cell}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ReplyMarkdown({ text }: { text: string }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      disallowedElements={["img"]}
      components={{
        table: ({ children }) => <Table>{children}</Table>,
        td: ({ children }) => <TableCell className="whitespace-normal">{children}</TableCell>,
        th: ({ children }) => (
          <TableHead scope="col" className="whitespace-normal">
            {children}
          </TableHead>
        ),
      }}
    >
      {text}
    </Markdown>
  );
}

const comparison = defineComponent({
  name: "Comparison",
  description: "Compare two finance concepts.",
  props: z.object({ title: label, headers: columns, rows }),
  component: ({ props }) => (
    <>
      <h3>{props.title}</h3>
      <ReplyTable title={props.title} headers={props.headers} data={props.rows} />
    </>
  ),
});

const headers = z.array(label).max(5);
const data = z.array(z.array(label).max(5)).max(16);
const answerArgs = z.tuple([z.string(), label, headers, data]);
const PortfolioContext = createContext<PortfolioSnapshot | undefined>(undefined);
function PortfolioDetails() {
  const snapshot = useContext(PortfolioContext);
  return snapshot ? <PortfolioBreakdown snapshot={snapshot} /> : null;
}

const PlotContext = createContext<StockSnapshot | undefined>(undefined);

function PerformanceChart() {
  const snapshot = useContext(PlotContext);
  if (!snapshot) return null;
  const plots = "stocks" in snapshot ? snapshot.stocks : [snapshot];
  return plots.map((plot, index) => <StockFigure key={index} plot={plot} />);
}

function StockFigure({ plot }: { plot: StockPlot }) {
  if (!plot?.points?.length) return null;
  const date = (index: number) => new Date(plot.points![index].time * 1000).toISOString().slice(0, 10);
  return (
    <figure>
      <figcaption className="text-sm text-muted-foreground">
        {plot.symbol} · {plot.currency ?? "Currency unavailable"} · {date(0)} – {date(plot.points.length - 1)} UTC ·
        Yahoo Finance
      </figcaption>
      <StockPriceChart
        symbol={plot.symbol}
        period={plot.period}
        currency={plot.currency}
        points={plot.points}
        tone="text-primary"
      />
    </figure>
  );
}

const answerComponent = defineComponent({
  name: "FinanceAnswer",
  description: "An explanation and optional financial data table.",
  props: z.object({ title: z.string(), explanation: label, headers, rows: data }),
  component: ({ props }) => (
    <article className="flex min-w-0 flex-col gap-3" data-finance-answer>
      {props.title && <h3>{props.title}</h3>}
      <div className="[&>*+*]:mt-2">
        <ReplyMarkdown text={props.explanation} />
      </div>
      <PerformanceChart />
      <PortfolioDetails />
      {props.rows?.length > 0 && props.headers && props.rows.every(Array.isArray) && (
        <ReplyTable title={props.title || "Financial data"} headers={props.headers} data={props.rows} />
      )}
    </article>
  ),
});
const library = createLibrary({ root: "FinanceAnswer", components: [answerComponent, comparison] });
const comparisonArgs = z.tuple([label, columns, rows]);

export function parseFinanceReply(answer: string) {
  const start = /^[ \t]*root\s*=\s*FinanceAnswer\(/m.exec(answer);
  if (start) {
    const intro = answer
      .slice(0, start.index)
      .replace(/(?:^|\n)`{3}(?:openui(?:-lang)?)?\s*$/, "")
      .trim();
    const code = answer.slice(start.index).trimStart();
    // A closing parenthesis inside a JSON string is part of the argument.
    const program = /^root\s*=\s*FinanceAnswer\(((?:"(?:\\.|[^"\\])*"|[^")])*)\)/.exec(code);
    if (program) {
      try {
        const values: unknown[] = JSON.parse(`[${program[1]}]`);
        const args = answerArgs.parse(values.slice(0, 4));
        const suggestions: unknown = values[4];
        const followUps = Array.isArray(suggestions)
          ? [...new Set(suggestions.filter((q): q is string => typeof q === "string")
              .map((q) => q.trim()).filter((q) => q.length > 0 && q.length <= 180))].slice(0, 3)
          : [];
        const [title, explanation, headers, rows] = args;
        const footer = code
          .slice(program[0].length)
          .trim()
          .replace(/^`{3}(?:\s|$)/, "")
          .trim();
        return {
          followUps,
          prose: intro,
          footer,
          ui: `root = FinanceAnswer(${args.map((value) => JSON.stringify(value)).join(", ")})`,
          copy: [intro, title, explanation, headers.join(" | "), ...rows.map((row) => row.join(" | ")), footer]
            .filter(Boolean)
            .join("\n\n"),
        };
      } catch {
        // Recover the readable explanation below if the model produced an invalid table.
      }
    }
    const opening = /^root\s*=\s*FinanceAnswer\(\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")/.exec(code);
    let prose = intro || "The response could not be displayed. Please ask again.";
    if (opening) {
      try {
        prose = [intro, JSON.parse(opening[2])].filter(Boolean).join("\n\n");
      } catch {
        // Keep the introduction when the explanation contains an invalid string escape.
      }
    }
    return { prose, copy: prose, partialProgram: code, intro };
  }
  const marker = /^\x60\x60\x60openui[ \t]*$/m.exec(answer);
  if (!marker) return { prose: answer, copy: answer };
  const prose = answer.slice(0, marker.index).trimEnd();
  const block = answer.slice(marker.index + marker[0].length).trim();
  const match = /^root\s*=\s*Comparison\(([\s\S]*)\)\s*\x60\x60\x60$/.exec(block);
  if (match) {
    try {
      const [title, headers, data] = comparisonArgs.parse(JSON.parse(`[${match[1]}]`));
      const args = [title, headers, data].map((value) => JSON.stringify(value)).join(", ");
      const copy = [prose, title, headers.join(" | "), ...data.map((row) => row.join(" | "))]
        .filter(Boolean)
        .join("\n\n");
      return { prose, copy, ui: `root = Comparison(${args})` };
    } catch {
      // A truncated or invalid optional table still leaves the standalone explanation.
    }
  }
  const fallback = prose || "The comparison could not be displayed. Please ask again.";
  return { prose: fallback, copy: fallback };
}

export function FinanceReply({
  reply,
  plot,
  portfolio,
  partial,
}: {
  reply: ReturnType<typeof parseFinanceReply>;
  portfolio?: PortfolioSnapshot;
  plot?: StockSnapshot;
  partial?: string;
}) {
  if (partial !== undefined && !reply.ui) {
    if ("partialProgram" in reply && reply.partialProgram)
      return (
        <>
          {reply.intro && <ReplyMarkdown text={reply.intro} />}
          <Renderer library={library} response={reply.partialProgram} isStreaming />
        </>
      );
    // Hold back an unfinished root declaration while its first tokens arrive.
    const boundary = partial.lastIndexOf("\n") + 1;
    const tail = partial.slice(boundary).trimStart().replace(/\s+/g, "");
    const visible = "root=FinanceAnswer(".startsWith(tail) ? partial.slice(0, boundary) : partial;
    return <ReplyMarkdown text={visible} />;
  }
  return (
    <PortfolioContext.Provider value={portfolio}>
      <PlotContext.Provider value={plot}>
        {reply.prose && <ReplyMarkdown text={reply.prose} />}
        {reply.ui && <Renderer library={library} response={reply.ui} isStreaming={partial !== undefined} />}
        {!reply.ui?.startsWith("root = FinanceAnswer(") && <PerformanceChart />}
        {!reply.ui?.startsWith("root = FinanceAnswer(") && <PortfolioDetails />}
        {"footer" in reply && reply.footer && <ReplyMarkdown text={reply.footer} />}
      </PlotContext.Provider>
    </PortfolioContext.Provider>
  );
}
