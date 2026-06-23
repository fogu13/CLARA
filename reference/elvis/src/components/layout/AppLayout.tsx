import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";

export function AppLayout({ title, children }: { title: string; children: React.ReactNode }) {
  const onboardWsId = useWorkspaceId();
  const { data: onboarded, isLoading: onboardLoading } = useQuery({
    queryKey: ["onboarded", onboardWsId],
    enabled: !!onboardWsId,
    queryFn: async () => {
      const { data } = await supabase.from("workspaces").select("onboarded").eq("id", onboardWsId!).single();
      return data?.onboarded ?? true; // fail-open: never trap a user out of the app
    },
  });
  if (onboardWsId && !onboardLoading && onboarded === false) {
    return <Navigate to="/welcome" replace />;
  }

  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />
      <div className="pl-60">
        <AppHeader title={title} />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
