"use client";

import { LogOut, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { authConfigured, signOut } from "@/lib/auth-client";

export function AppHeader() {
  const router = useRouter();

  function handleSignOut() {
    signOut();
    router.replace("/auth");
  }

  return (
    <header className="flex h-14 items-center justify-end gap-3 border-b bg-card px-6">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
        <User className="h-4 w-4 text-primary" />
      </div>
      {authConfigured && (
        <Button variant="ghost" size="sm" className="gap-2" onClick={handleSignOut}>
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      )}
    </header>
  );
}
