"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import {
  LayoutDashboard,
  MessageSquare,
  Lightbulb,
  Tags,
  ScrollText,
  CheckCircle,
  GraduationCap,
  Database,
  Plug,
  ShieldCheck,
  Settings,
  Rocket,
} from "lucide-react";

type NavKey =
  | "dashboard" | "signals" | "insights" | "actions" | "learnings"
  | "onboarding" | "sources" | "integrations" | "taxonomy" | "rules" | "compliance" | "settings";
type GroupKey = "work" | "setup" | "govern";

const NAV_GROUPS: {
  label: GroupKey | null;
  items: { href: string; key: NavKey; icon: typeof LayoutDashboard }[];
}[] = [
  {
    label: null,
    items: [{ href: "/dashboard", key: "dashboard", icon: LayoutDashboard }],
  },
  {
    label: "work",
    items: [
      { href: "/signals", key: "signals", icon: MessageSquare },
      { href: "/insights", key: "insights", icon: Lightbulb },
      { href: "/actions", key: "actions", icon: CheckCircle },
      { href: "/learnings", key: "learnings", icon: GraduationCap },
    ],
  },
  {
    label: "setup",
    items: [
      { href: "/onboarding", key: "onboarding", icon: Rocket },
      { href: "/sources", key: "sources", icon: Database },
      { href: "/integrations", key: "integrations", icon: Plug },
      { href: "/taxonomy", key: "taxonomy", icon: Tags },
      { href: "/rules", key: "rules", icon: ScrollText },
    ],
  },
  {
    label: "govern",
    items: [
      { href: "/compliance", key: "compliance", icon: ShieldCheck },
      { href: "/settings", key: "settings", icon: Settings },
    ],
  },
];

export function AppSidebar({ open = false, onClose }: { open?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <>
      {open ? (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          aria-hidden="true"
          onClick={onClose}
        />
      ) : null}
      <aside
        className={cn(
          "w-64 flex-col border-r bg-card",
          "max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:shadow-xl",
          open ? "flex" : "hidden md:flex"
        )}
      >
      <div className="flex h-14 items-center gap-2 border-b px-6">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-sm font-bold text-primary-foreground">C</span>
        </div>
        <span className="font-semibold text-foreground">CLARA</span>
      </div>
      <nav className="flex-1 space-y-4 p-3">
        {NAV_GROUPS.map((group, groupIndex) => (
          <div key={group.label ?? `group-${groupIndex}`} className="space-y-1">
            {group.label ? (
              <p className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wider text-muted-foreground/70">
                {t.nav[group.label]}
              </p>
            ) : null}
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                  onClick={onClose}
                >
                  <Icon className="h-4 w-4" />
                  {t.nav[item.key]}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">{t.nav.tagline}</p>
      </div>
      </aside>
    </>
  );
}
