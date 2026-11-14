"use client";

import { ChevronRight, MessageSquare, SquarePen } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { SidebarMenuButton, SidebarMenuItem, useSidebar } from "@/components/ui/sidebar";

import { listThreads } from "../../chat/actions";

function dateGroup(date: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const time = new Date(date).getTime();
  if (time >= today.getTime()) return "Today";
  today.setDate(today.getDate() - 1);
  if (time >= today.getTime()) return "Yesterday";
  today.setDate(today.getDate() - 6);
  return time >= today.getTime() ? "Previous 7 days" : "Older";
}

export function ChatHistoryNav() {
  const pathname = usePathname();
  const query = useSearchParams();
  const threadId = query.get("thread");
  const onChat = pathname === "/dashboard/chat";
  const { state, isMobile, setOpenMobile } = useSidebar();
  const compact = !isMobile && state === "collapsed";
  const [expanded, setExpanded] = useState(onChat);
  const [popover, setPopover] = useState(false);
  const [search, setSearch] = useState("");
  const [threads, setThreads] = useState<Awaited<ReturnType<typeof listThreads>>["threads"]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const open = compact ? popover : expanded;

  useEffect(() => {
    if (onChat) setExpanded(true);
  }, [onChat]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    async function refresh() {
      try {
        const result = await listThreads();
        if (active) {
          setThreads(result.threads);
          setStatus("ready");
        }
      } catch {
        if (active) setStatus("error");
      }
    }
    void refresh();
    window.addEventListener("finance-chat-saved", refresh);
    return () => {
      active = false;
      window.removeEventListener("finance-chat-saved", refresh);
    };
  }, [open, threadId]);

  function closeNavigation() {
    setPopover(false);
    setSearch("");
    if (isMobile) setOpenMobile(false);
  }

  const selected = onChat ? (query.get("thread") ?? threads[0]?.id) : null;
  const groups = Object.groupBy(
    threads.filter((t) => t.title.toLowerCase().includes(search.trim().toLowerCase())),
    (t) => dateGroup(t.updatedAt),
  );
  const history = (
    <nav aria-label="Sidebar chat history" className="flex max-h-72 flex-col gap-1 overflow-y-auto px-2 py-1">
      <SidebarMenuButton asChild isActive={selected === "new"}>
        <Link
          prefetch={false}
          href="/dashboard/chat?thread=new"
          onClick={() => {
            closeNavigation();
            if (onChat && query.get("thread") === "new") window.dispatchEvent(new Event("finance-chat-new"));
          }}
        >
          <SquarePen />
          New chat
        </Link>
      </SidebarMenuButton>
      <Input
        aria-label="Search chats"
        placeholder="Search chats…"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {Object.entries(groups).map(([label, items]) => (
        <div key={label}>
          <p className="px-2 pt-2 text-xs text-muted-foreground">{label}</p>
          {items?.map((thread) => (
            <SidebarMenuButton key={thread.id} asChild isActive={thread.id === selected}>
              <Link
                href={`/dashboard/chat?thread=${thread.id}`}
                prefetch={false}
                onClick={closeNavigation}
                aria-current={thread.id === selected ? "page" : undefined}
                title={thread.title}
              >
                <span className="truncate">{thread.title}</span>
              </Link>
            </SidebarMenuButton>
          ))}
        </div>
      ))}
      {(!Object.keys(groups).length || status === "error") && (
        <p className="p-2 text-xs text-muted-foreground">
          {status === "error"
            ? "Could not load chats."
            : status === "loading"
              ? "Loading chats…"
              : search
                ? "No matching chats."
                : "No saved chats yet."}
        </p>
      )}
    </nav>
  );
  const trigger = (
    <SidebarMenuButton tooltip="Finance chat" aria-label="Finance chat" isActive={onChat}>
      <MessageSquare />
      <span>Finance chat</span>
      {!compact && <ChevronRight className={expanded ? "ml-auto rotate-90" : "ml-auto"} />}
    </SidebarMenuButton>
  );
  return (
    <SidebarMenuItem>
      {compact ? (
        <Popover open={popover} onOpenChange={setPopover}>
          <PopoverTrigger asChild>{trigger}</PopoverTrigger>
          <PopoverContent side="right" align="start" className="w-64 p-1">
            {history}
          </PopoverContent>
        </Popover>
      ) : (
        <Collapsible open={expanded} onOpenChange={setExpanded}>
          <CollapsibleTrigger asChild>{trigger}</CollapsibleTrigger>
          <CollapsibleContent className="ml-4 border-l">{history}</CollapsibleContent>
        </Collapsible>
      )}
    </SidebarMenuItem>
  );
}
