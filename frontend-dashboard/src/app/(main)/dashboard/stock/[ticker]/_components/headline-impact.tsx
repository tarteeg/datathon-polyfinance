"use client";

import Link from "next/link";
import { useId, useState, useTransition } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { checkHeadline, followHeadline, type Headline, type Impact, type Replay } from "@/server/headline-impact";

export function HeadlineImpact({ headline, demo = false }: { headline: Headline; demo?: boolean }) {
  const [open, setOpen] = useState(false);
  const [include, setInclude] = useState(true);
  const [stage, setStage] = useState<Replay>("august");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [pending, start] = useTransition();
  const checkboxId = useId();

  function load(nextStage: Replay, nextInclude: boolean) {
    setStage(nextStage);
    setInclude(nextInclude);
    setImpact(null);
    setSaved(null);
    setError("");
    start(async () => {
      try {
        const response = await checkHeadline(headline.url, demo ? nextStage : undefined, nextInclude);
        setImpact(response.result);
        setSaved(response.saved);
      } catch {
        setError("Couldn’t check this headline. Please try again.");
      }
    });
  }

  function follow() {
    setError("");
    start(async () => {
      try {
        setSaved(await followHeadline(headline.url, demo ? stage : undefined, include));
      } catch {
        setError("Couldn’t save this question. Please try again.");
      }
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) load(stage, include);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="h-auto max-w-full self-start py-1 whitespace-normal">
          Why does this matter to my portfolio?
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader className="pr-6">
          <DialogDescription>
            {demo ? "Historical replay · fictional portfolio" : "Your portfolio · headline impact"}
          </DialogDescription>
          <DialogTitle className="text-xl leading-snug">{impact?.title ?? headline.title}</DialogTitle>
          <DialogDescription>
            <a href={headline.url} target="_blank" rel="noreferrer">
              Read the headline source
            </a>
            {(impact ? impact.published : headline.published) && ` · ${impact ? impact.published : headline.published}`}
          </DialogDescription>
        </DialogHeader>
        {demo && (
          <div className="grid gap-2 rounded-lg border p-3">
            <span className="font-medium">Simulated portfolio · CA$50,000</span>
            <label htmlFor={checkboxId} className="flex items-center gap-2">
              <Checkbox
                id={checkboxId}
                checked={include}
                disabled={pending}
                onCheckedChange={(value) => load(stage, value === true)}
              />
              Include CA$5,000 of Chemtrade
            </label>
            <span className="text-muted-foreground">{include ? "CA$45,000" : "CA$50,000"} in cash</span>
            <span>Evidence as of {stage === "august" ? "August 22" : "November 14"}, 2024</span>
          </div>
        )}
        <div aria-live="polite" aria-busy={pending} className="grid gap-3">
          {pending && <p role="status">{impact ? "Saving question…" : "Checking portfolio and sources…"}</p>}
          {error && (
            <p role="alert" className="text-destructive">
              {error}
            </p>
          )}
          {error && !impact && (
            <Button variant="outline" disabled={pending} onClick={() => load(stage, include)}>
              Retry
            </Button>
          )}
          {impact && (
            <>
              {!demo && <p className="text-sm text-muted-foreground">{{
                full: "Based on the full article", excerpt: "Based on a publisher excerpt",
                unknown: "The feed did not identify whether this is the full article",
                missing: "Based on the available headline and feed metadata",
              }[impact.source_content_type]}</p>}
              {impact.connections.map((item) => (
                <div key={item.ticker} className="grid gap-1">
                  <h3 className="font-semibold">{item.ticker} · Portfolio relevance</h3>
                  <p>{item.explanation}</p>
                  <blockquote className="border-l-2 pl-3 text-sm text-muted-foreground">
                    {{ article: "Article", headline: "Headline", feed_summary: "StocksFeed summary",
                       issuer_note: "Issuer disclosure summary", results_note: "Quarterly results summary" }[item.quote_source]}
                    {" · “"}{item.quote}”
                  </blockquote>
                </div>
              ))}
              {impact.links.map((link) => (
                <div key={link.ticker} className="grid gap-1">
                  <h3 className="font-semibold">{link.ticker} · documented dependency</h3>
                  <p>{link.text}</p>
                  <a className="text-muted-foreground underline" href={link.url} target="_blank" rel="noreferrer">
                    Issuer disclosure · {link.published}
                  </a>
                </div>
              ))}
              {impact.direct.length > 0 && (
                <p>
                  <strong>Tagged holdings</strong> · {impact.direct.join(", ")}. StocksFeed associates these companies
                  with the article.
                </p>
              )}
              {Boolean(impact.watchlist?.length) && (
                <p>
                  <strong>On your watchlist</strong> · {impact.watchlist?.join(", ")}. You track these shares without
                  a recorded quantity.
                </p>
              )}
              {!impact.connections.length && !(demo && impact.links.length) && (
                <p>The available evidence didn’t establish how this event affects your holdings or watchlist.</p>
              )}
              {impact.question && (
                <p>
                  <strong>What to watch</strong>
                  <br />
                  {impact.question}
                </p>
              )}
              {impact.update && (
                <div className="grid gap-1 rounded-lg bg-muted p-3">
                  <h3 className="font-semibold">What happened next</h3>
                  <p>{impact.update.text}</p>
                  <a className="underline" href={impact.update.url} target="_blank" rel="noreferrer">
                    Quarterly results · {impact.update.published}
                  </a>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                {impact.question &&
                  (saved ? (
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/dashboard/chat?thread=${saved}`}>Open followed question</Link>
                    </Button>
                  ) : (
                    <Button size="sm" disabled={pending} onClick={follow}>
                      Follow this question
                    </Button>
                  ))}
                {demo && (impact.question || stage === "november") && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={pending}
                    onClick={() => load(stage === "august" ? "november" : "august", include)}
                  >
                    {stage === "august" ? "Advance to November results" : "Return to August"}
                  </Button>
                )}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
