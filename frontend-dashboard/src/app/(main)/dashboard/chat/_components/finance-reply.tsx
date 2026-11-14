import { createLibrary, defineComponent, Renderer } from "@openuidev/react-lang";
import Markdown from "react-markdown";
import { z } from "zod";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const label = z.string().trim().min(1);
const columns = z.tuple([label, label, label]);
const rows = z.array(columns).min(1).max(8);
const comparison = defineComponent({
  name: "Comparison",
  description: "Compare two finance concepts across a few dimensions.",
  props: z.object({ title: label, headers: columns, rows }),
  component: ({ props }) => (
    <Table>
      <TableCaption className="caption-top text-left">{props.title}</TableCaption>
      <TableHeader>
        <TableRow>
          {props.headers.map((header, index) => (
            <TableHead key={index} scope="col" className="whitespace-normal">
              {header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {props.rows.map((row, index) => (
          <TableRow key={index}>
            {row.map((cell, column) => (
              <TableCell key={column} className="whitespace-normal align-top">
                {cell}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
});
const library = createLibrary({ root: "Comparison", components: [comparison] });
const comparisonArgs = z.tuple([label, columns, rows]);

export function parseFinanceReply(answer: string) {
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

export function FinanceReply({ reply }: { reply: ReturnType<typeof parseFinanceReply> }) {
  return (
    <>
      <Markdown skipHtml disallowedElements={["img"]}>
        {reply.prose}
      </Markdown>
      {reply.ui && <Renderer library={library} response={reply.ui} />}
    </>
  );
}
