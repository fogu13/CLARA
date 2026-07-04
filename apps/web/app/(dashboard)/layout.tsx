import type { ReactNode } from "react";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";
import { AuthGuard } from "@/components/auth/auth-guard";
import { I18nProvider } from "@/lib/i18n";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <I18nProvider>
        <div className="flex min-h-screen bg-background">
          <AppSidebar />
          <div className="flex flex-1 flex-col">
            <AppHeader />
            <main className="flex-1 overflow-auto p-6">{children}</main>
          </div>
        </div>
      </I18nProvider>
    </AuthGuard>
  );
}
