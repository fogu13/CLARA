import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { Json } from "@/integrations/supabase/types";
import type { FeedbackRule } from "@/lib/types";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { RelevantLearnings } from "@/components/rules/RelevantLearnings";
import { logEvent } from "@/lib/events";

// Option vocabularies mirror src/lib/types.ts and the evaluate-rules condition matcher.
const CATEGORIES = ["content_clarity", "product_issue", "churn_risk", "campaign_performance",
  "ux_friction", "sentiment_shift", "engagement_drop", "positive_trend", "compliance_concern"];
const LEVELS = ["low", "medium", "high", "critical"];
const TEAMS = ["marketing", "product", "cx", "sales", "engineering"];
const ACTION_TYPES = ["notify", "create_ticket", "create_segment", "draft_email"] as const;

type ActionDraft = {
  type: string;
  name_template?: string;
  subject?: string;
  template_id?: string;
  project?: string;
  labels?: string;
  recipients?: string;
  channels?: string;
};

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rule?: FeedbackRule | null;
  workspaceId: number;
}

const csv = (s?: string) => (s ?? "").split(",").map((x) => x.trim()).filter(Boolean);
const join = (a?: unknown) => (Array.isArray(a) ? a.join(", ") : "");

export function RuleBuilderDialog({ open, onOpenChange, rule, workspaceId }: Props) {
  const qc = useQueryClient();
  const isEdit = !!rule;

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [urgency, setUrgency] = useState<string[]>([]);
  const [severity, setSeverity] = useState<string[]>([]);
  const [teams, setTeams] = useState<string[]>([]);
  const [minImpact, setMinImpact] = useState("");
  const [minConfidence, setMinConfidence] = useState("");
  const [minContacts, setMinContacts] = useState("");
  const [actions, setActions] = useState<ActionDraft[]>([{ type: "notify", channels: "slack" }]);
  const [autoExecute, setAutoExecute] = useState(false);
  const [priority, setPriority] = useState("0");
  const [measureAfterDays, setMeasureAfterDays] = useState("14");

  // Hydrate state whenever the dialog opens (create = blank, edit = existing rule).
  useEffect(() => {
    if (!open) return;
    const c = (rule?.conditions ?? {}) as Record<string, unknown>;
    setName(rule?.name ?? "");
    setDescription(rule?.description ?? "");
    setCategories((c.insight_category as string[]) ?? []);
    setUrgency((c.urgency as string[]) ?? []);
    setSeverity((c.severity as string[]) ?? []);
    setTeams((c.target_team as string[]) ?? []);
    setMinImpact(c.min_impact_score != null ? String(c.min_impact_score) : "");
    setMinConfidence(c.min_confidence != null ? String(c.min_confidence) : "");
    setMinContacts(c.min_affected_contacts != null ? String(c.min_affected_contacts) : "");
    setAutoExecute(rule?.auto_execute ?? false);
    setPriority(String(rule?.priority ?? 0));
    setMeasureAfterDays(String(rule?.measure_after_days ?? 14));
    setActions(
      rule?.actions?.length
        ? (rule.actions as Record<string, unknown>[]).map((a) => ({
            type: String(a.type ?? "notify"),
            name_template: a.name_template as string | undefined,
            subject: a.subject as string | undefined,
            template_id: a.template_id as string | undefined,
            project: a.project as string | undefined,
            labels: join(a.labels),
            recipients: join(a.recipients),
            channels: join(a.channels) || "slack",
          }))
        : [{ type: "notify", channels: "slack" }],
    );
  }, [open, rule]);

  const toggle = (list: string[], set: (v: string[]) => void, value: string) =>
    set(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

  function buildConditions(): Record<string, unknown> {
    const c: Record<string, unknown> = {};
    if (categories.length) c.insight_category = categories;
    if (urgency.length) c.urgency = urgency;
    if (severity.length) c.severity = severity;
    if (teams.length) c.target_team = teams;
    if (minImpact !== "") c.min_impact_score = Number(minImpact);
    if (minConfidence !== "") c.min_confidence = Number(minConfidence);
    if (minContacts !== "") c.min_affected_contacts = Number(minContacts);
    return c;
  }

  function buildActions(): Record<string, unknown>[] {
    return actions.map((a) => {
      switch (a.type) {
        case "create_segment":
          return { type: a.type, name_template: a.name_template || "Segment for {insight_title}" };
        case "draft_email":
          return { type: a.type, subject: a.subject || "Re: {insight_title}", template_id: a.template_id };
        case "create_ticket":
          return { type: a.type, project: a.project || "OPS", labels: csv(a.labels) };
        case "notify":
        default:
          return { type: a.type, channels: csv(a.channels).length ? csv(a.channels) : ["slack"], recipients: csv(a.recipients) };
      }
    });
  }

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        workspace_id: workspaceId,
        name: name.trim(),
        description: description.trim() || null,
        conditions: buildConditions() as unknown as Json,
        actions: buildActions() as unknown as Json,
        auto_execute: autoExecute,
        priority: Number(priority) || 0,
        measure_after_days: Number(measureAfterDays) || 14,
      };
      if (isEdit) {
        const { error } = await supabase.from("feedback_rules").update(payload).eq("id", rule!.id).eq("workspace_id", workspaceId);
        if (error) throw error;
      } else {
        const { error } = await supabase.from("feedback_rules").insert(payload);
        if (error) throw error;
      }
    },
    onSuccess: () => {
      toast.success(isEdit ? "Rule updated" : "Rule created");
      logEvent(workspaceId, isEdit ? "rule_updated" : "rule_created", { entity: "rule", metadata: { name: name.trim() } });
      qc.invalidateQueries({ queryKey: ["rules", workspaceId] });
      onOpenChange(false);
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to save rule"),
  });

  const onSave = () => {
    if (!name.trim()) return toast.error("Give the rule a name");
    if (Object.keys(buildConditions()).length === 0) return toast.error("Add at least one condition");
    if (actions.length === 0) return toast.error("Add at least one action");
    save.mutate();
  };

  const Chips = ({ options, value, set }: { options: string[]; value: string[]; set: (v: string[]) => void }) => (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => toggle(value, set, o)}
          className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
            value.includes(o) ? "bg-primary text-primary-foreground border-primary" : "bg-background text-muted-foreground border-border hover:bg-secondary"
          }`}
        >
          {o.replace(/_/g, " ")}
        </button>
      ))}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit rule" : "Create rule"}</DialogTitle>
          <DialogDescription>
            When an insight matches all conditions, the actions run (automatically or after approval).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="grid grid-cols-1 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="rule-name">Name</Label>
              <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Route critical churn risk to CX" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rule-desc">Description (optional)</Label>
              <Textarea id="rule-desc" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </div>
          </div>

          {/* Conditions */}
          <div className="space-y-3 rounded-lg border bg-secondary/30 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Conditions (match all)</p>
            <div className="space-y-1.5"><Label className="text-xs">Insight category</Label><Chips options={CATEGORIES} value={categories} set={setCategories} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label className="text-xs">Urgency</Label><Chips options={LEVELS} value={urgency} set={setUrgency} /></div>
              <div className="space-y-1.5"><Label className="text-xs">Severity</Label><Chips options={LEVELS} value={severity} set={setSeverity} /></div>
            </div>
            <div className="space-y-1.5"><Label className="text-xs">Target team</Label><Chips options={TEAMS} value={teams} set={setTeams} /></div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5"><Label className="text-xs">Min impact (0–10)</Label><Input type="number" value={minImpact} onChange={(e) => setMinImpact(e.target.value)} placeholder="—" /></div>
              <div className="space-y-1.5"><Label className="text-xs">Min confidence (0–1)</Label><Input type="number" step="0.05" value={minConfidence} onChange={(e) => setMinConfidence(e.target.value)} placeholder="—" /></div>
              <div className="space-y-1.5"><Label className="text-xs">Min affected</Label><Input type="number" value={minContacts} onChange={(e) => setMinContacts(e.target.value)} placeholder="—" /></div>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-3 rounded-lg border bg-secondary/30 p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Actions</p>
              <Button type="button" size="sm" variant="outline" onClick={() => setActions((a) => [...a, { type: "notify", channels: "slack" }])}>
                <Plus className="h-3.5 w-3.5 mr-1" />Add action
              </Button>
            </div>
            {actions.map((a, i) => (
              <div key={i} className="rounded-md border bg-background p-2.5 space-y-2">
                <div className="flex items-center gap-2">
                  <Select value={a.type} onValueChange={(v) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, type: v } : x)))}>
                    <SelectTrigger className="h-8 w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>{ACTION_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>)}</SelectContent>
                  </Select>
                  {actions.length > 1 && (
                    <Button type="button" size="icon" variant="ghost" className="h-8 w-8 ml-auto" onClick={() => setActions((arr) => arr.filter((_, j) => j !== i))}>
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  )}
                </div>
                {a.type === "notify" && (
                  <div className="grid grid-cols-2 gap-2">
                    <Input placeholder="channels (slack, email)" value={a.channels ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, channels: e.target.value } : x)))} />
                    <Input placeholder="recipients (#cx, pm@co)" value={a.recipients ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, recipients: e.target.value } : x)))} />
                  </div>
                )}
                {a.type === "create_ticket" && (
                  <div className="grid grid-cols-2 gap-2">
                    <Input placeholder="project (e.g. PROD)" value={a.project ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, project: e.target.value } : x)))} />
                    <Input placeholder="labels (bug, churn)" value={a.labels ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, labels: e.target.value } : x)))} />
                  </div>
                )}
                {a.type === "create_segment" && (
                  <Input placeholder="segment name template" value={a.name_template ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, name_template: e.target.value } : x)))} />
                )}
                {a.type === "draft_email" && (
                  <div className="grid grid-cols-2 gap-2">
                    <Input placeholder="subject" value={a.subject ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, subject: e.target.value } : x)))} />
                    <Input placeholder="template id" value={a.template_id ?? ""} onChange={(e) => setActions((arr) => arr.map((x, j) => (j === i ? { ...x, template_id: e.target.value } : x)))} />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Execution settings */}
          <div className="grid grid-cols-3 gap-3 items-end">
            <div className="space-y-1.5">
              <Label className="text-xs">Priority</Label>
              <Input type="number" value={priority} onChange={(e) => setPriority(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Measure after (days)</Label>
              <Input type="number" value={measureAfterDays} onChange={(e) => setMeasureAfterDays(e.target.value)} />
            </div>
            <div className="flex items-center gap-2 pb-2">
              <Switch checked={autoExecute} onCheckedChange={setAutoExecute} id="auto" />
              <Label htmlFor="auto" className="text-xs">Auto-execute (no approval)</Label>
            </div>
          </div>

          <RelevantLearnings workspaceId={workspaceId} categories={categories} />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={onSave} disabled={save.isPending}>{save.isPending ? "Saving…" : isEdit ? "Save changes" : "Create rule"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
