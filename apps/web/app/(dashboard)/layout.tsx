"use client";

import { useState, type ReactNode } from "react";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";
import { AuthGuard } from "@/components/auth/auth-guard";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);
  return (
    <AuthGuard>
        {/* h-dvh + overflow-hidden keeps the sidebar and header in place while
            only <main> scrolls; min-h-screen let the whole document scroll and
            carried the navigation off-screen on long pages. */}
        <div className="flex h-dvh overflow-hidden bg-background">
          <AppSidebar open={navOpen} onClose={() => setNavOpen(false)} />
          <div className="flex flex-1 flex-col min-w-0">
            <AppHeader onMenuClick={() => setNavOpen(true)} />
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
        </div>
    </AuthGuard>
  );
}
