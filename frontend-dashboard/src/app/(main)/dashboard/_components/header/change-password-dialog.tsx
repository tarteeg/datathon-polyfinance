"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authClient } from "@/lib/auth-client";

export function ChangePasswordDialog() {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    const data = new FormData(event.currentTarget);
    const currentPassword = String(data.get("currentPassword"));
    const newPassword = String(data.get("newPassword"));
    if (newPassword !== data.get("confirmation")) {
      setError("The new passwords don’t match.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const result = await authClient.changePassword({ currentPassword, newPassword, revokeOtherSessions: true });
      if (result.error) {
        setError(result.error.code === "INVALID_PASSWORD"
          ? "Your current password is incorrect."
          : result.error.message || "Couldn’t change your password. Try again.");
        return;
      }
      setOpen(false);
      toast.success("Password changed.");
    } catch {
      setError("Couldn’t connect. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => {
      if (saving) return;
      setError("");
      setOpen(next);
    }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">Change password</Button>
      </DialogTrigger>
      <DialogContent showCloseButton={!saving}>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>Use 8–128 characters. Changing your password signs out your other sessions.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} onChange={() => setError("")} className="grid gap-4">
          <fieldset disabled={saving} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="current-password">Current password</Label>
              <Input id="current-password" name="currentPassword" type="password" autoComplete="current-password" required />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="new-password">New password</Label>
              <Input id="new-password" name="newPassword" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <Input id="confirm-password" name="confirmation" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
            </div>
          </fieldset>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline" disabled={saving}>Cancel</Button></DialogClose>
            <Button type="submit" disabled={saving}>{saving ? "Changing…" : "Change password"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
