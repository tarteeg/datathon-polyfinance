"use client";

import { CircleUserRound, Settings, SlidersHorizontal } from "lucide-react";
import { useRouter } from "next/navigation";
import { type ReactElement, useState } from "react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authClient } from "@/lib/auth-client";
import { getInitials } from "@/lib/utils";

import { ChangePasswordDialog } from "./change-password-dialog";
import { LayoutControls } from "./layout-controls";

const sections = [
  { title: "Account", icon: CircleUserRound },
  { title: "Preferences", icon: SlidersHorizontal },
] as const;

type Profile = { name: string; email: string; avatar: string };

export function SettingsDialog({ user, children }: { user: Profile; children?: ReactElement }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {children ?? <Button size="icon" aria-label="Open settings"><Settings /></Button>}
      </DialogTrigger>
      <DialogContent className="flex h-dvh max-w-none flex-col gap-0 overflow-hidden rounded-none p-0 sm:h-[min(760px,calc(100dvh-2rem))] sm:max-w-4xl sm:rounded-xl md:flex-row">
        <SettingsPanels user={user} />
      </DialogContent>
    </Dialog>
  );
}

function SettingsPanels({ user }: { user: Profile }) {
  const [section, setSection] = useState<(typeof sections)[number]["title"]>("Account");

  return (
    <>
      <aside className="flex shrink-0 flex-col border-b bg-muted/30 p-3 md:w-[220px] md:border-r md:border-b-0">
        <DialogTitle className="px-2 pt-2 pb-4">Settings</DialogTitle>
        <DialogDescription className="sr-only">Manage your account and dashboard preferences.</DialogDescription>
        <nav aria-label="Settings sections" className="flex gap-1 md:flex-col">
          {sections.map(({ title, icon: Icon }) => (
            <Button
              key={title}
              size="sm"
              variant={section === title ? "secondary" : "ghost"}
              aria-current={section === title ? "page" : undefined}
              className="justify-start"
              onClick={() => setSection(title)}
            >
              <Icon /> {title}
            </Button>
          ))}
        </nav>
        <div className="mt-auto hidden items-center gap-2.5 border-t px-2 pt-3 md:flex">
          <Avatar className="size-8 rounded-lg">
            <AvatarImage src={user.avatar || undefined} alt="" />
            <AvatarFallback>{getInitials(user.name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="truncate font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
        </div>
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <h2 className="border-b px-4 py-4 text-xl font-semibold tracking-tight sm:px-6">{section}</h2>
        <div className="min-h-0 flex-1 overflow-y-auto bg-muted/20 p-4 sm:p-6">
          <div className="rounded-xl border bg-card p-4 text-card-foreground sm:p-5">
            {section === "Account" ? (
              <>
                <AccountProfile user={user} />
                <div className="mt-5 flex items-center justify-between gap-3 border-t pt-4">
                  <h3 className="font-medium">Password</h3>
                  <ChangePasswordDialog />
                </div>
              </>
            ) : <LayoutControls />}
          </div>
        </div>
      </div>
    </>
  );
}

function AccountProfile({ user }: { user: Profile }) {
  const router = useRouter();
  const [name, setName] = useState(user.name);
  const [saving, setSaving] = useState(false);

  return (
    <form
      className="flex flex-col items-start gap-4"
      onSubmit={async (event) => {
        event.preventDefault();
        const trimmed = name.trim();
        if (!trimmed || saving) return;
        setSaving(true);
        try {
          const { error } = await authClient.updateUser({ name: trimmed });
          if (error) throw new Error();
          setName(trimmed);
          router.refresh();
          toast.success("Name updated.");
        } catch {
          toast.error("Couldn’t update your name. Try again.");
        } finally {
          setSaving(false);
        }
      }}
    >
      <h3 className="font-medium">Personal information</h3>
      <div className="grid w-full gap-2">
        <Label htmlFor="settings-full-name">Full name</Label>
        <Input id="settings-full-name" autoComplete="name" value={name} required disabled={saving}
          onChange={(event) => setName(event.target.value)} />
      </div>
      <div className="grid min-w-0 gap-1">
        <p className="font-medium">Email address</p>
        <p className="break-all text-muted-foreground">{user.email}</p>
      </div>
      <Button type="submit" size="sm" disabled={saving || !name.trim() || name.trim() === user.name}>
        {saving ? "Saving…" : "Save changes"}
      </Button>
    </form>
  );
}
