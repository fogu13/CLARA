import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { loadSampleData } from "@/lib/sample-data";

const WelcomePage = () => {
  const workspaceId = useWorkspaceId();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [withSample, setWithSample] = useState(true);
  const [busy, setBusy] = useState(false);

  const finish = async () => {
    if (!workspaceId) return;
    setBusy(true);
    try {
      const update: { onboarded: boolean; name?: string } = { onboarded: true };
      if (name.trim()) update.name = name.trim();
      const { error } = await supabase.from("workspaces").update(update).eq("id", workspaceId);
      if (error) throw error;
      if (withSample) {
        const n = await loadSampleData(workspaceId);
        toast.success(`Loaded ${n} sample signals.`);
      }
      qc.invalidateQueries();
      navigate("/app");
    } catch (e) {
      toast.error("Could not finish setup", { description: e instanceof Error ? e.message : undefined });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-xl border border-border p-6">
        <h1 className="text-xl font-semibold">Welcome to Odradek</h1>
        <p className="mt-1 text-sm text-muted-foreground">Let's set up your workspace. Takes 10 seconds.</p>
        <div className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="ws">Workspace name</Label>
            <Input id="ws" placeholder="e.g. Acme Inc" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="sample">Load sample data</Label>
              <p className="text-xs text-muted-foreground">A few example signals so you can explore right away.</p>
            </div>
            <Switch id="sample" checked={withSample} onCheckedChange={setWithSample} />
          </div>
        </div>
        <Button className="mt-6 w-full" disabled={busy || !workspaceId} onClick={finish}>
          {busy ? "Setting up…" : "Get started"}
        </Button>
      </div>
    </div>
  );
};

export default WelcomePage;
