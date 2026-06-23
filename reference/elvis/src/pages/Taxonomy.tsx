import { useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Upload, Wand2, Sparkles, ShieldCheck } from "lucide-react";
import { parseTaxonomyFile, buildTree, slugify, coverage } from "@/lib/taxonomy";
import type { TaxonomyNode } from "@/lib/types";
import { TaxonomyTree } from "@/components/taxonomy/TaxonomyTree";
import { ReviewQueue } from "@/components/taxonomy/ReviewQueue";

const TaxonomyPage = () => {
  const workspaceId = useWorkspaceId();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["taxonomy", workspaceId],
    enabled: !!workspaceId,
    queryFn: async () => {
      const { data: nodes, error } = await supabase
        .from("taxonomy_nodes").select("*").eq("workspace_id", workspaceId!).neq("status", "merged");
      if (error) throw error;
      const { count: mapped } = await supabase
        .from("signal_node_map").select("id", { count: "exact", head: true });
      const { count: total } = await supabase
        .from("signals").select("id", { count: "exact", head: true }).eq("workspace_id", workspaceId!);
      const counts = new Map<string, number>();
      const { data: maps } = await supabase.from("signal_node_map").select("node_id");
      (maps ?? []).forEach((m: { node_id: string }) => counts.set(m.node_id, (counts.get(m.node_id) ?? 0) + 1));
      const withCounts = (nodes as TaxonomyNode[]).map((n) => ({ ...n, match_count: counts.get(n.id) ?? 0 }));
      return { tree: buildTree(withCounts.filter((n) => n.status !== "candidate")), coverage: coverage(mapped ?? 0, total ?? 0), nodes: withCounts };
    },
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const rows = parseTaxonomyFile(await file.text(), file.type || (file.name.endsWith(".json") ? "application/json" : "text/csv"));
      const cache = new Map<string, string>();
      const ensure = async (parentId: string | null, level: number, name: string, description = "") => {
        const slug = slugify(name);
        if (!slug) return null;
        const key = `${parentId ?? "root"}/${slug}`;
        if (cache.has(key)) return cache.get(key)!;
        const { data: ins, error } = await supabase.from("taxonomy_nodes")
          .upsert({ workspace_id: workspaceId!, parent_id: parentId, level, name, slug, description: description || null, origin: "uploaded", created_by: "user" },
                  { onConflict: "workspace_id,parent_id,slug" })
          .select("id").single();
        if (error) throw error;
        cache.set(key, ins.id);
        return ins.id as string;
      };
      for (const r of rows) {
        const cId = await ensure(null, 1, r.category);
        const tId = r.theme ? await ensure(cId, 2, r.theme) : null;
        if (r.subtheme) await ensure(tId ?? cId, tId ? 3 : 2, r.subtheme, r.description);
      }
      await supabase.functions.invoke("embed-taxonomy", { body: { workspace_id: workspaceId } });
      return rows.length;
    },
    onSuccess: (n) => {
      qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] });
      toast.success(`Imported ${n} taxonomy row(s). Embedding in the background.`);
    },
    onError: (e) => toast.error("Taxonomy import failed", { description: e instanceof Error ? e.message : undefined }),
  });

  // Map existing (unmapped) signals to taxonomy nodes via embeddings only — no LLM enrichment,
  // so this works even when the chat model is rate-limited.
  const backfill = useMutation({
    mutationFn: async () => {
      const res = await supabase.functions.invoke("backfill-mappings", { body: { workspace_id: workspaceId, limit: 200 } });
      if (res.error) throw res.error;
      if (res.data?.error) throw new Error(res.data.error);
      return res.data as { scanned: number; mapped: number };
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] });
      toast.success(`Mapped ${d.mapped} of ${d.scanned} signal(s) to taxonomy nodes.`);
    },
    onError: (e) => toast.error("Mapping failed", { description: e instanceof Error ? e.message : undefined }),
  });

  const discover = useMutation({
    mutationFn: async () => {
      const res = await supabase.functions.invoke("evolve-taxonomy", { body: { workspace_id: workspaceId, limit: 200 } });
      if (res.error) throw res.error;
      if (res.data?.error) throw new Error(res.data.error);
      return res.data as { candidates: number };
    },
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] }); toast.success(`Discovered ${d.candidates} candidate theme(s).`); },
    onError: (e) => toast.error("Discovery failed", { description: e instanceof Error ? e.message : undefined }),
  });

  const governance = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.rpc("apply_taxonomy_governance", { p_workspace_id: workspaceId! });
      if (error) throw error;
      return data as { promoted: number; merged: number; archived: number };
    },
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] }); toast.success(`Governance: ${d.promoted} promoted, ${d.merged} merged, ${d.archived} archived.`); },
    onError: (e) => toast.error("Governance failed", { description: e instanceof Error ? e.message : undefined }),
  });

  const undo = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from("taxonomy_nodes").update({ status: "candidate", auto_promoted: false }).eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] }); toast.success("Reverted to candidate"); },
    onError: (e) => toast.error("Undo failed", { description: e instanceof Error ? e.message : undefined }),
  });

  return (
    <AppLayout title="Taxonomy">
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-muted-foreground">
          Your company themes. {data ? `Coverage: ${Math.round(data.coverage * 100)}% of signals mapped.` : ""}
        </p>
        <input ref={fileRef} type="file" accept=".csv,.json" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = ""; }} />
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={discover.isPending || !workspaceId} onClick={() => discover.mutate()}>
            <Sparkles className="h-3.5 w-3.5 mr-1.5" />{discover.isPending ? "Discovering…" : "Discover themes"}
          </Button>
          <Button variant="outline" size="sm" disabled={governance.isPending || !workspaceId} onClick={() => governance.mutate()}>
            <ShieldCheck className="h-3.5 w-3.5 mr-1.5" />{governance.isPending ? "Running…" : "Run governance"}
          </Button>
          <Button variant="outline" size="sm" disabled={backfill.isPending || !workspaceId} onClick={() => backfill.mutate()}>
            <Wand2 className="h-3.5 w-3.5 mr-1.5" />{backfill.isPending ? "Mapping…" : "Map signals"}
          </Button>
          <Button variant="outline" size="sm" disabled={upload.isPending || !workspaceId} onClick={() => fileRef.current?.click()}>
            <Upload className="h-3.5 w-3.5 mr-1.5" />{upload.isPending ? "Importing…" : "Upload taxonomy"}
          </Button>
        </div>
      </div>
      {data && (
        <ReviewQueue
          workspaceId={workspaceId!}
          candidates={(data.nodes as TaxonomyNode[]).filter((n) => n.status === "candidate")}
          activeNodes={(data.nodes as TaxonomyNode[]).filter((n) => n.status === "active")}
        />
      )}
      <div className="rounded-lg border border-border p-4">
        {isLoading ? <Skeleton className="h-40 w-full" /> : <TaxonomyTree nodes={data?.tree ?? []} onUndo={(id) => undo.mutate(id)} />}
      </div>
    </AppLayout>
  );
};

export default TaxonomyPage;
