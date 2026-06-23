import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { Json } from "@/integrations/supabase/types";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

interface WorkspaceSettings {
  notification_email?: string;
  slack_webhook?: string;
  measurement_window_days?: number;
  anomaly_zscore?: number;
}

const SettingsPage = () => {
  const workspaceId = useWorkspaceId();
  const qc = useQueryClient();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [email, setEmail] = useState("");
  const [slack, setSlack] = useState("");
  const [windowDays, setWindowDays] = useState("14");
  const [zscore, setZscore] = useState("2.0");

  const { data: workspace, isLoading } = useQuery({
    queryKey: ["workspace", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("workspaces")
        .select("*")
        .eq("id", workspaceId!)
        .single();
      if (error) throw error;
      return data;
    },
    enabled: !!workspaceId,
  });

  useEffect(() => {
    if (!workspace) return;
    const s = (workspace.settings ?? {}) as WorkspaceSettings;
    setName(workspace.name ?? "");
    setSlug(workspace.slug ?? "");
    setEmail(s.notification_email ?? "");
    setSlack(s.slack_webhook ?? "");
    setWindowDays(String(s.measurement_window_days ?? 14));
    setZscore(String(s.anomaly_zscore ?? 2.0));
  }, [workspace]);

  const save = useMutation({
    mutationFn: async () => {
      const settings: WorkspaceSettings = {
        notification_email: email.trim() || undefined,
        slack_webhook: slack.trim() || undefined,
        measurement_window_days: Number(windowDays) || 14,
        anomaly_zscore: Number(zscore) || 2.0,
      };
      const { error } = await supabase
        .from("workspaces")
        .update({ name: name.trim(), slug: slug.trim(), settings: settings as unknown as Json })
        .eq("id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Settings saved");
      qc.invalidateQueries({ queryKey: ["workspace", workspaceId] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to save settings"),
  });

  if (isLoading) {
    return (
      <AppLayout title="Settings">
        <div className="max-w-2xl space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-2/3" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Settings">
      <div className="max-w-2xl space-y-8">
        <div>
          <h2 className="text-lg font-semibold mb-1">Workspace</h2>
          <p className="text-sm text-muted-foreground mb-4">Manage your workspace settings.</p>
          <div className="space-y-4">
            <div>
              <Label htmlFor="ws-name">Workspace Name</Label>
              <Input id="ws-name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5 max-w-sm" />
            </div>
            <div>
              <Label htmlFor="ws-slug">Slug</Label>
              <Input id="ws-slug" value={slug} onChange={(e) => setSlug(e.target.value)} className="mt-1.5 max-w-sm" />
            </div>
          </div>
        </div>

        <Separator />

        <div>
          <h2 className="text-lg font-semibold mb-1">Notifications</h2>
          <p className="text-sm text-muted-foreground mb-4">Configure where notifications are sent.</p>
          <div className="space-y-4">
            <div>
              <Label htmlFor="email">Notification Email</Label>
              <Input id="email" type="email" placeholder="team@company.com" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5 max-w-sm" />
            </div>
            <div>
              <Label htmlFor="slack">Slack Webhook URL</Label>
              <Input id="slack" placeholder="https://hooks.slack.com/..." value={slack} onChange={(e) => setSlack(e.target.value)} className="mt-1.5 max-w-sm" />
            </div>
          </div>
        </div>

        <Separator />

        <div>
          <h2 className="text-lg font-semibold mb-1">Analysis Settings</h2>
          <p className="text-sm text-muted-foreground mb-4">Tune the feedback analysis engine.</p>
          <div className="space-y-4">
            <div>
              <Label htmlFor="window">Measurement Window (days)</Label>
              <Input id="window" type="number" value={windowDays} onChange={(e) => setWindowDays(e.target.value)} className="mt-1.5 max-w-[120px]" />
            </div>
            <div>
              <Label htmlFor="zscore">Anomaly Z-Score Threshold</Label>
              <Input id="zscore" type="number" step={0.1} value={zscore} onChange={(e) => setZscore(e.target.value)} className="mt-1.5 max-w-[120px]" />
            </div>
          </div>
        </div>

        <div className="pt-4">
          <Button onClick={() => save.mutate()} disabled={save.isPending || !workspaceId}>
            {save.isPending ? "Saving…" : "Save Settings"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
};

export default SettingsPage;
