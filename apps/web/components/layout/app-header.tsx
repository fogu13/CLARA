"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronDown, LogOut, Menu, User } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { authConfigured, currentUserEmail, currentUserRole, signOut } from "@/lib/auth-client";
import { LanguageToggle, useI18n } from "@/lib/i18n";

type NavKey =
  | "dashboard" | "signals" | "insights" | "actions" | "learnings"
  | "onboarding" | "sources" | "integrations" | "taxonomy" | "rules"
  | "compliance" | "aiLiteracy" | "settings";

const SECTION_BY_SEGMENT: Record<string, NavKey> = {
  dashboard: "dashboard",
  signals: "signals",
  insights: "insights",
  actions: "actions",
  learnings: "learnings",
  onboarding: "onboarding",
  sources: "sources",
  integrations: "integrations",
  taxonomy: "taxonomy",
  rules: "rules",
  compliance: "compliance",
  "ai-literacy": "aiLiteracy",
  settings: "settings",
};

export function AppHeader({ onMenuClick }: { onMenuClick?: () => void }) {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useI18n();
  // Identity comes from localStorage / the session cookie, so it only exists
  // client-side; reading it during render would mismatch the server HTML.
  const [email, setEmail] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    setEmail(currentUserEmail());
    setRole(currentUserRole());
  }, []);

  function handleSignOut() {
    signOut();
    router.replace("/auth");
  }

  const sectionKey = SECTION_BY_SEGMENT[pathname.split("/")[1] ?? ""];

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-card px-4 md:px-6">
      <button
        type="button"
        className="md:hidden rounded-md p-2 text-muted-foreground hover:bg-accent"
        aria-label={t.common.openNav}
        onClick={onMenuClick}
      >
        <Menu className="h-5 w-5" />
      </button>
      {sectionKey ? (
        <span className="text-sm font-semibold text-foreground">{t.nav[sectionKey]}</span>
      ) : null}
      <div className="flex-1" />
      <LanguageToggle />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label={t.common.accountMenu}
            className="flex items-center gap-1 rounded-full p-1 pr-1.5 transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
              <User className="h-4 w-4 text-primary" aria-hidden="true" />
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          <DropdownMenuLabel>
            <p className="truncate font-medium">{email ?? t.common.signedIn}</p>
            {role ? <p className="mt-0.5 text-xs font-normal capitalize text-muted-foreground">{role}</p> : null}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/settings">{t.nav.settings}</Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/ai-literacy">{t.nav.aiLiteracy}</Link>
          </DropdownMenuItem>
          {authConfigured ? (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={handleSignOut}>
                <LogOut className="h-4 w-4" aria-hidden="true" />
                {t.nav.signOut}
              </DropdownMenuItem>
            </>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
