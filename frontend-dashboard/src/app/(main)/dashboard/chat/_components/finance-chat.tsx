"use client";

import { useEffect, useRef, useState } from "react";
import {
  ChatProvider,
  EventType,
  type Message as ChatMessage,
  type StreamProtocolAdapter,
  useThread,
  useThreadList,
} from "@openuidev/react-headless";

import { useRouter } from "next/navigation";
import type { ChartSnapshot } from "../chart-snapshot";
import { SavedChart } from "./saved-chart";
import { FinanceReply, parseFinanceReply } from "./finance-reply";
import { ArrowUp, ArrowUpRight, Check, ChevronDown, Copy, Plus } from "lucide-react";

import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Button } from "@/components/ui/button";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupTextarea } from "@/components/ui/input-group";
import { Message } from "@/components/ui/message";
import {
  MessageScroller,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";

import { ActivityTimeline } from "./activity-timeline";
import { type ChatActivity, readChatStream } from "@/lib/chat-stream";
import { type StockSnapshot, listThreads, loadHistory } from "../actions";

import type { PortfolioSnapshot } from "./portfolio-breakdown";

type Evidence = { activity?: ChatActivity[]; stockPlot?: StockSnapshot; portfolio?: PortfolioSnapshot };

export function FinanceChat({ requestedThread }: { requestedThread?: string }) {
  const [liveEvidence, setLiveEvidence] = useState<Record<string, Evidence>>({});
  const replyAdapter: StreamProtocolAdapter = {
    async *parse(response) {
      const messageId = response.headers.get("x-message-id") ?? crypto.randomUUID();
      yield { type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" };
      for await (const event of readChatStream(response)) {
        if (event.error) throw new Error(event.error);
        if (event.activity) {
          const step: ChatActivity = event.activity;
          setLiveEvidence((previous) => {
            const prior = previous[messageId];
            const steps = new Map(prior?.activity?.map((item) => [item.id, item]));
            steps.set(step.id, step);
            return { ...previous, [messageId]: { ...prior, activity: [...steps.values()] } };
          });
          continue;
        }
        if (event.done) {
          if (event.stock || event.portfolio)
            setLiveEvidence((previous) => ({
              ...previous,
              [messageId]: { ...previous[messageId], stockPlot: event.stock, portfolio: event.portfolio },
            }));
          window.dispatchEvent(new Event("finance-chat-saved"));
          yield { type: EventType.TEXT_MESSAGE_END, messageId };
          return;
        }
        if (event.delta) yield { type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: event.delta };
      }
      throw new Error("The reply was interrupted. Reload the conversation to retry.");
    },
  };
  return (
    <ChatProvider
      fetchThreadList={listThreads}
      createThread={async (message) => ({
        id: crypto.randomUUID(),
        title: String(message.content).slice(0, 72),
        createdAt: Date.now(),
      })}
      loadThread={async (id) =>
        (await loadHistory(id)).flatMap<ChatMessage>(
          ({ turn, question, answer, chart_snapshot, stock_snapshot, portfolio_snapshot, tool_activity }) => [
            { id: `q-${turn}`, role: "user", content: question },
            {
              id: `a-${turn}`,
              role: "assistant",
              content: answer,
              snapshot: chart_snapshot,
              activity: tool_activity,
              stockPlot: stock_snapshot,
              portfolio: portfolio_snapshot,
            },
          ],
        )
      }
      processMessage={async ({ threadId, messages, abortController }) => {
        const question = messages.at(-1)?.content;
        if (typeof question !== "string") throw new Error("Enter a message.");
        const completed = messages.filter((message) => message.role === "assistant").length;
        const response = await fetch("/api/finance-chat", {
          method: "POST",
          signal: abortController.signal,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ threadId, question, lastTurn: completed }),
        });
        if (!response.ok)
          throw new Error(
            response.status === 409 ? "Your chat changed. Reload the conversation." : "The assistant is unavailable.",
          );
        return response;
      }}
      streamProtocol={replyAdapter}
    >
      <Conversation requestedThread={requestedThread} liveEvidence={liveEvidence} />
    </ChatProvider>
  );
}

const starters = [
  "What does it mean to own a stock?",
  "How is my portfolio doing today?",
  "Compare Apple and Microsoft over the past month.",
  "Which energy companies are getting the most news coverage this week?",
];

function CopyReply({ text }: { text: string }) {
  const [feedback, setFeedback] = useState("");
  useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(() => setFeedback(""), 1800);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Copy response"
        title="Copy response"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(text);
            setFeedback("Copied");
          } catch {
            setFeedback("Could not copy");
          }
        }}
      >
        {feedback === "Copied" ? <Check /> : <Copy />}
      </Button>
      <span role="status">{feedback}</span>
    </div>
  );
}

function Conversation({
  requestedThread,
  liveEvidence,
}: {
  requestedThread?: string;
  liveEvidence: Record<string, Evidence>;
}) {
  const router = useRouter();
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const { threads, selectedThreadId, selectThread, switchToNewThread, loadThreads, isLoadingThreads, threadListError } =
    useThreadList();
  const { messages, processMessage, isRunning, isLoadingMessages, threadError } = useThread();
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [ready, setReady] = useState(false);
  const initialSelection = useRef(true);
  const busy = sending || isRunning || isLoadingMessages || isLoadingThreads;
  useEffect(() => {
    loadThreads();
  }, [loadThreads]);
  useEffect(() => {
    if (isLoadingThreads) setReady(true);
    if (ready && !isLoadingThreads && initialSelection.current) {
      initialSelection.current = false;
      const target = requestedThread ? threads.find((thread) => thread.id === requestedThread) : threads[0];
      if (target) selectThread(target.id);
    }
  }, [isLoadingThreads, ready, threads, selectThread, requestedThread]);

  useEffect(() => {
    if (!sending && !isRunning && selectedThreadId && messages.at(-1)?.role === "assistant" && !threadError) {
      const url = new URL(window.location.href);
      if (
        url.pathname === "/dashboard/chat" &&
        (!url.searchParams.has("thread") || url.searchParams.get("thread") === "new")
      ) {
        url.searchParams.set("thread", selectedThreadId);
        router.replace(url.pathname + url.search, { scroll: false });
      }
    }
  }, [sending, isRunning, selectedThreadId, messages, threadError, router]);

  const title = threads.find((thread) => thread.id === selectedThreadId)?.title ?? "New chat";

  async function submit(question = draft) {
    if (busy || threadError || !question.trim()) return;
    setDraft(question);
    setSending(true);
    await processMessage({ role: "user", content: question.trim() });
    if (!mounted.current) return;
    setSending(false);
    loadThreads();
  }

  // OpenUI keeps the optimistic question on failure so the user can see what to retry.
  useEffect(() => {
    if (!threadError && !sending && !isRunning && messages.at(-1)?.role === "assistant") setDraft("");
  }, [sending, isRunning, messages, threadError]);

  useEffect(() => {
    function clearNewChat() {
      if (busy) return;
      setDraft("");
      switchToNewThread();
    }
    window.addEventListener("finance-chat-new", clearNewChat);
    return () => window.removeEventListener("finance-chat-new", clearNewChat);
  }, [busy, switchToNewThread]);

  function openThread(id?: string) {
    setDraft("");
    if (id === selectedThreadId) return;
    if (!id && requestedThread === "new") switchToNewThread();
    else router.push(`/dashboard/chat?thread=${id ?? "new"}`);
  }

  return (
    <section className="mx-auto flex h-[calc(100dvh-10rem)] min-h-72 w-full max-w-3xl flex-col gap-4">
      <header className="flex min-w-0 items-center justify-between gap-2 border-b pb-3">
        <h1 className="sr-only">Finance chat</h1>
        <Sheet>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              className="min-w-0 justify-start"
              aria-label={`Open chat history: ${title}`}
              title={title}
            >
              <span className="truncate">{title}</span>
              <ChevronDown data-icon="inline-end" />
            </Button>
          </SheetTrigger>
          <SheetContent aria-describedby={undefined}>
            <SheetHeader>
              <SheetTitle>Chat history</SheetTitle>
            </SheetHeader>
            <nav aria-label="Chat history" className="flex min-h-0 flex-col gap-1 overflow-y-auto px-3 pb-4">
              {threads.map((thread) => (
                <SheetClose asChild key={thread.id}>
                  <Button
                    variant={thread.id === selectedThreadId ? "secondary" : "ghost"}
                    aria-current={thread.id === selectedThreadId ? "page" : undefined}
                    disabled={busy}
                    className="justify-start"
                    title={thread.title}
                    onClick={() => openThread(thread.id)}
                  >
                    <span className="truncate">{thread.title}</span>
                  </Button>
                </SheetClose>
              ))}
              {!threads.length && (
                <p className="px-2 text-sm text-muted-foreground">
                  {isLoadingThreads
                    ? "Loading chats…"
                    : threadListError
                      ? "Could not load chats."
                      : "No saved chats yet."}
                </p>
              )}
            </nav>
          </SheetContent>
        </Sheet>
        <Button variant="outline" size="sm" className="shrink-0" disabled={busy} onClick={() => openThread()}>
          <Plus data-icon="inline-start" />
          New chat
        </Button>
      </header>
      <MessageScrollerProvider autoScroll>
        <MessageScroller className="min-h-0 flex-1">
          <MessageScrollerViewport>
            <MessageScrollerContent className="gap-6 px-1 py-4" role="log" aria-label="Conversation">
              {ready && !messages.length && !isLoadingThreads && !isLoadingMessages && !threadError && (
                <div className="m-auto flex w-full max-w-md flex-col items-start gap-4">
                  <h2 className="text-2xl font-semibold tracking-tight">What would you like to explore?</h2>
                  <div className="flex w-full flex-col gap-2">
                    {starters.map((question) => (
                      <Button
                        key={question}
                        variant="outline"
                        className="h-auto justify-between gap-3 whitespace-normal py-2.5 text-left"
                        disabled={busy}
                        onClick={() => void submit(question)}
                      >
                        {question}
                        <ArrowUpRight data-icon="inline-end" />
                      </Button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((message) => {
                const { id, role, content } = message;
                const snapshot = (message as ChatMessage & { snapshot?: ChartSnapshot }).snapshot;
                const streaming = isRunning && role === "assistant" && id === messages.at(-1)?.id;
                const reply = role === "assistant" && typeof content === "string" ? parseFinanceReply(content) : null;
                return (
                  <MessageScrollerItem key={id} messageId={id}>
                    <Message align={role === "user" ? "end" : "start"}>
                      {role === "user" ? (
                        <Bubble>
                          <BubbleContent className="whitespace-pre-wrap">
                            <span className="sr-only">You: </span>
                            {typeof content === "string" ? content : ""}
                          </BubbleContent>
                        </Bubble>
                      ) : (
                        <div className="min-w-0 flex-1 wrap-anywhere text-base leading-7 [&>*+*]:mt-3 [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-6 [&_ol]:pl-6 [&_li+li]:mt-1 [&_a]:underline [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_:is(h1,h2,h3,h4,h5,h6)]:font-semibold">
                          <span className="sr-only">Assistant: </span>
                          <ActivityTimeline
                            steps={(message as ChatMessage & Evidence).activity ?? liveEvidence[id]?.activity}
                            streaming={streaming}
                          />
                          {reply && (
                            <>
                              <FinanceReply
                                partial={streaming && typeof content === "string" ? content : undefined}
                                reply={reply}
                                portfolio={(message as ChatMessage & Evidence).portfolio ?? liveEvidence[id]?.portfolio}
                                plot={(message as ChatMessage & Evidence).stockPlot ?? liveEvidence[id]?.stockPlot}
                              />
                              {snapshot && (
                                <>
                                  <SavedChart snapshot={snapshot} />
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={busy || Boolean(threadError)}
                                    onClick={() => void submit("Show related news")}
                                  >
                                    Show related news
                                  </Button>
                                </>
                              )}
                              {!streaming && <CopyReply text={reply.copy} />}
                              {!busy && !threadError && id === messages.at(-1)?.id && Boolean(reply.followUps?.length) && (
                                <div role="group" aria-label="Suggested follow-up questions" className="flex flex-wrap gap-2">
                                  {reply.followUps?.map((question) => (
                                    <Button key={question} variant="outline" size="sm"
                                      className="h-auto max-w-full py-1.5 text-left whitespace-normal"
                                      onClick={() => void submit(question)}>
                                      {question}
                                      <ArrowUpRight data-icon="inline-end" />
                                    </Button>
                                  ))}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </Message>
                  </MessageScrollerItem>
                );
              })}
              {((isRunning &&
                !messages.at(-1)?.content &&
                !liveEvidence[messages.at(-1)?.id ?? ""]?.activity?.length) ||
                (isRunning && messages.at(-1)?.role === "user") ||
                isLoadingMessages) && (
                <p role="status" className="text-muted-foreground text-sm">
                  {isLoadingMessages ? "Loading conversation…" : "Thinking…"}
                </p>
              )}
            </MessageScrollerContent>
          </MessageScrollerViewport>
        </MessageScroller>
      </MessageScrollerProvider>
      {(threadError || threadListError) && (
        <p role="alert" className="text-destructive text-sm">
          {threadError?.message ?? "Could not load chat history."}
        </p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
        className="flex gap-2"
      >
        <InputGroup className="rounded-2xl p-1">
          <InputGroupTextarea
            rows={1}
            className="min-h-10 max-h-40"
            aria-label="Message"
            placeholder="Ask a finance question…"
            maxLength={4000}
            readOnly={busy}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <InputGroupAddon align="inline-end" className="self-end">
            <InputGroupButton
              type="submit"
              variant="default"
              size="icon-sm"
              aria-label="Send"
              title="Send"
              disabled={busy || !draft.trim() || Boolean(threadError)}
            >
              <ArrowUp />
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
      </form>
      {threadError && (
        <Button
          variant="outline"
          disabled={busy}
          onClick={() => {
            if (selectedThreadId) selectThread(selectedThreadId);
            else switchToNewThread();
          }}
        >
          Reload conversation
        </Button>
      )}
    </section>
  );
}
