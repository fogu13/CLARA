"use client";

import { useState, type ReactNode } from "react";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";
import { AuthGuard } from "@/components/auth/auth-guard";
import { I18nProvider } from "@/lib/i18n";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);
  return (
    <AuthGuard>
      <I18nProvider>
        <div className="flex min-h-screen bg-background">
          <AppSidebar open={navOpen} onClose={() => setNavOpen(false)} />
          <div className="flex flex-1 flex-col min-w-0">
            <AppHeader onMenuClick={() => setNavOpen(true)} />
            <main className="flex-1 overflow-auto p-6">{children}</main>
          </div>
        </div>
      </I18nProvider>
    </AuthGuard>
  );
}
