"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
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
} from "lucide-react";

const NAV_GROUPS: {
  label: string | null;
  items: { href: string; label: string; icon: typeof LayoutDashboard }[];
}[] = [
  {
    label: null,
    items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Work",
    items: [
      { href: "/signals", label: "Signals", icon: MessageSquare },
      { href: "/insights", label: "Insights", icon: Lightbulb },
      { href: "/actions", label: "Actions", icon: CheckCircle },
      { href: "/learnings", label: "Learnings", icon: GraduationCap },
    ],
  },
  {
    label: "Setup",
    items: [
      { href: "/sources", label: "Sources", icon: Database },
      { href: "/integrations", label: "Integrations", icon: Plug },
      { href: "/taxonomy", label: "Taxonomy", icon: Tags },
      { href: "/rules", label: "Rules", icon: ScrollText },
    ],
  },
  {
    label: "Govern",
    items: [
      { href: "/compliance", label: "Compliance", icon: ShieldCheck },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 flex-col border-r bg-card">
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
                {group.label}
              </p>
            ) : null}
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">Feedback-to-Action Platform</p>
      </div>
    </aside>
  );
}
