"use client";

import { LogOut, Menu, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { authConfigured, signOut } from "@/lib/auth-client";
import { LanguageToggle, useI18n } from "@/lib/i18n";

export function AppHeader({ onMenuClick }: { onMenuClick?: () => void }) {
  const router = useRouter();
  const { t } = useI18n();

  function handleSignOut() {
    signOut();
    router.replace("/auth");
  }

  return (
    <header className="flex h-14 items-center gap-3 border-b bg-card px-4 md:px-6">
      <button
        type="button"
        className="md:hidden rounded-md p-2 text-muted-foreground hover:bg-accent"
        aria-label="Open navigation"
        onClick={onMenuClick}
      >
        <Menu className="h-5 w-5" />
      </button>
      <div className="flex-1" />
      <LanguageToggle />
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
        <User className="h-4 w-4 text-primary" />
      </div>
      {authConfigured && (
        <Button variant="ghost" size="sm" className="gap-2" onClick={handleSignOut}>
          <LogOut className="h-4 w-4" />
          {t.nav.signOut}
        </Button>
      )}
    </header>
  );
}
