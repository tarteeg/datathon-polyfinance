"use client";

import { useState } from "react";

import { LogOut } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import { authClient } from "@/lib/auth-client";
import { getInitials } from "@/lib/utils";

import { SettingsDialog } from "../header/settings-dialog";

export function NavUser({
  user,
}: {
  readonly user: {
    readonly name: string;
    readonly email: string;
    readonly avatar: string;
  };
}) {
  const [isSigningOut, setIsSigningOut] = useState(false);

  async function signOut() {
    setIsSigningOut(true);
    try {
      const { error } = await authClient.signOut();
      if (error) {
        toast.error("Unable to log out. Please try again.");
        return;
      }
      window.location.replace("/auth/v1/login");
    } catch {
      toast.error("Unable to log out. Please try again.");
    } finally {
      setIsSigningOut(false);
    }
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SettingsDialog user={user}>
          <SidebarMenuButton size="lg" aria-label={`Open settings for ${user.name}`}>
            <Avatar className="h-8 w-8 rounded-lg grayscale">
              <AvatarImage src={user.avatar || undefined} alt={user.name} />
              <AvatarFallback className="rounded-lg">{getInitials(user.name)}</AvatarFallback>
            </Avatar>
            <div className="grid flex-1 text-left text-sm leading-tight">
              <span className="truncate font-medium">{user.name}</span>
              <span className="text-muted-foreground truncate text-xs">{user.email}</span>
            </div>
          </SidebarMenuButton>
        </SettingsDialog>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton onClick={signOut} disabled={isSigningOut} tooltip="Log out">
          <LogOut />
          <span>{isSigningOut ? "Logging out…" : "Log out"}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
