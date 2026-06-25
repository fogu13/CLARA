"use client";

import { Bell, LogOut, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authConfigured, signOut } from "@/lib/auth-client";

export function AppHeader() {
  const router = useRouter();

  function handleSignOut() {
    signOut();
    router.replace("/auth");
  }

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-card px-6">
      <div className="flex flex-1 items-center gap-3">
        <Search className="h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search signals, insights, actions..."
          className="h-9 max-w-md"
        />
      </div>
      <Button variant="ghost" size="icon">
        <Bell className="h-4 w-4" />
      </Button>
      <div className="flex items-center gap-2">
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
          <span className="text-xs font-semibold text-primary">U</span>
        </div>
        {authConfigured && (
          <Button variant="ghost" size="icon" onClick={handleSignOut} title="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
}
