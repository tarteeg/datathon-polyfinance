"use client";

import { ArrowDownRight, Loader2, Search, Wrench } from "lucide-react";
import { useId, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock, CodeBlockContent } from "@/components/ui/code-block";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Table, TableCell, TableHead } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { runInvestigation } from "@/server/investigate-actions";
import type { InvestigateResult } from "@/server/riskripple";

// Matches the finance-chat reply's markdown pattern (dashboard/chat/_components/finance-reply.tsx)
// for visual consistency -- the agent's answer is real markdown, not plain text.
function AnswerMarkdown({ text }: { text: string }) {
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

export function InvestigateForm({ defaultTickers }: { defaultTickers: string }) {
  const id = useId();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<InvestigateResult | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Describe the event</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-4"
            onSubmit={async (event) => {
              event.preventDefault();
              if (pending) return;
              const form = new FormData(event.currentTarget);
              setPending(true);
              setError("");
              setResult(null);
              try {
                const outcome = await runInvestigation(form);
                if (!outcome.ok) {
                  setError(outcome.error);
                } else {
                  setResult(outcome.data);
                  if (outcome.data.error) setError(outcome.data.error);
                }
              } catch {
                setError("Couldn’t reach the investigation agent. Try again.");
              } finally {
                setPending(false);
              }
            }}
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor={`${id}-event`}>Event or scenario</FieldLabel>
                <Textarea
                  id={`${id}-event`}
                  name="event_description"
                  rows={3}
                  placeholder="e.g. New export controls restrict advanced semiconductor equipment sales to a major chip-manufacturing hub."
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor={`${id}-tickers`}>Portfolio holdings (tickers)</FieldLabel>
                <Input
                  id={`${id}-tickers`}
                  name="tickers"
                  defaultValue={defaultTickers}
                  placeholder="NVDA, AMD, INTC"
                  required
                />
              </Field>
            </FieldGroup>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <Button type="submit" disabled={pending} className="self-start">
              {pending ? <Loader2 className="animate-spin" /> : <Search />}
              {pending ? "Investigating…" : "Investigate"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Findings</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {result.error ? (
              <p className="text-destructive text-sm">{result.error}</p>
            ) : (
              <div className="text-sm [&>*+*]:mt-2">
                <AnswerMarkdown text={result.answer ?? ""} />
              </div>
            )}

            {!!result.trace.length && (
              <Collapsible className="flex flex-col gap-2">
                <CollapsibleTrigger className="text-muted-foreground flex items-center gap-2 text-xs hover:underline">
                  <Wrench className="size-3.5" />
                  Show how the agent got this ({result.trace.length} steps)
                </CollapsibleTrigger>
                <CollapsibleContent>
                <Trace>
                  {result.trace.flatMap((message, i) =>
                    message.content.map((block, j) => {
                      const key = `${i}-${j}`;
                      if (block.type === "text") {
                        if (message.role !== "assistant") return null;
                        return (
                          <p key={key} className="text-muted-foreground text-sm">
                            {block.text}
                          </p>
                        );
                      }
                      if (block.type === "tool_use") {
                        return (
                          <TraceCollapsible key={key}>
                            <TraceCollapsibleTrigger>
                              <TraceLine>
                                <TraceIcon>
                                  <Wrench />
                                </TraceIcon>
                                <TraceTitle>{block.name ?? "tool call"}</TraceTitle>
                              </TraceLine>
                            </TraceCollapsibleTrigger>
                            <TraceCollapsibleContent>
                              <CodeBlock size="sm">
                                <CodeBlockContent wrap>{JSON.stringify(block.input ?? {}, null, 2)}</CodeBlockContent>
                              </CodeBlock>
                            </TraceCollapsibleContent>
                          </TraceCollapsible>
                        );
                      }
                      if (block.type === "tool_result") {
                        const content =
                          typeof block.content === "string" ? block.content : JSON.stringify(block.content, null, 2);
                        return (
                          <TraceCollapsible key={key}>
                            <TraceCollapsibleTrigger>
                              <TraceLine status={block.status === "error" ? "error" : undefined}>
                                <TraceIcon>
                                  <ArrowDownRight />
                                </TraceIcon>
                                <TraceTitle>result{block.status ? ` (${block.status})` : ""}</TraceTitle>
                              </TraceLine>
                            </TraceCollapsibleTrigger>
                            <TraceCollapsibleContent>
                              <CodeBlock size="sm">
                                <CodeBlockContent wrap>{content}</CodeBlockContent>
                              </CodeBlock>
                            </TraceCollapsibleContent>
                          </TraceCollapsible>
                        );
                      }
                      return null;
                    }),
                  )}
                </Trace>
                </CollapsibleContent>
              </Collapsible>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
