"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollText, Plus, Trash2, X } from "lucide-react";
import { createRule, deleteRule, getRules } from "@/lib/client-api";
import type { FeedbackRule, RuleAction, RuleCondition } from "@/lib/types";

type Draft = Omit<FeedbackRule, "rule_id">;

const OPERATORS = ["equals", "not_equals", "contains"];
const ACTION_TYPES = ["create_ticket", "notify", "create_segment", "governance_block"];

function emptyDraft(): Draft {
  return {
    name: "",
    priority: 0,
    is_active: true,
    conditions: [{ field: "", operator: "equals", value: "" }],
    actions: [{ type: "create_ticket", target: "" }]
  };
}

function summarize(rule: FeedbackRule): string {
  const ifPart = rule.conditions.length
    ? rule.conditions.map((c) => `${c.field || "?"} ${c.operator} ${c.value || "?"}`).join(" AND ")
    : "any signal";
  const thenPart = rule.actions.length
    ? rule.actions.map((a) => `${a.type}${a.target ? ` → ${a.target}` : ""}`).join(", ")
    : "no action";
  return `If ${ifPart} → ${thenPart}`;
}

export default function RulesPage() {
  const [rules, setRules] = useState<FeedbackRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState<{ tone: "idle" | "busy" | "error"; message: string }>({ tone: "idle", message: "" });

  useEffect(() => {
    getRules().then(setRules).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function refresh() {
    try {
      setRules(await getRules());
    } catch {
      /* keep current */
    }
  }

  function setCondition(index: number, patch: Partial<RuleCondition>) {
    setDraft((d) => (d ? { ...d, conditions: d.conditions.map((c, i) => (i === index ? { ...c, ...patch } : c)) } : d));
  }
  function setAction(index: number, patch: Partial<RuleAction>) {
    setDraft((d) => (d ? { ...d, actions: d.actions.map((a, i) => (i === index ? { ...a, ...patch } : a)) } : d));
  }

  async function save() {
    if (!draft || !draft.name.trim()) {
      setStatus({ tone: "error", message: "Give the rule a name." });
      return;
    }
    setStatus({ tone: "busy", message: "Saving…" });
    try {
      await createRule({
        ...draft,
        conditions: draft.conditions.filter((c) => c.field.trim() || c.value.trim()),
        actions: draft.actions.filter((a) => a.type.trim())
      });
      setDraft(null);
      setStatus({ tone: "idle", message: "" });
      await refresh();
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : "Couldn't save the rule." });
    }
  }

  async function remove(ruleId: string) {
    try {
      await deleteRule(ruleId);
      await refresh();
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : "Couldn't delete the rule." });
    }
  }

  if (loading) return <div className="text-muted-foreground">Loading rules...</div>;

  const busy = status.tone === "busy";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Rules</h1>
          <p className="text-sm text-muted-foreground mt-1">Automation rules for triage and action routing</p>
        </div>
        <Button size="sm" disabled={!!draft} onClick={() => setDraft(emptyDraft())}>
          <Plus className="h-4 w-4 mr-2" />
          New Rule
        </Button>
      </div>

      {status.message ? (
        <div
          className={`rounded-md border p-3 text-sm ${
            status.tone === "error"
              ? "border-destructive/40 bg-destructive/5 text-destructive"
              : "border-border bg-muted text-muted-foreground"
          }`}
        >
          {status.message}
        </div>
      ) : null}

      {draft ? (
        <Card>
          <CardHeader><CardTitle className="text-base">New rule</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
              <div>
                <Label htmlFor="rule-name">Name</Label>
                <Input
                  id="rule-name"
                  className="mt-1"
                  value={draft.name}
                  onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="rule-priority">Priority</Label>
                <Input
                  id="rule-priority"
                  type="number"
                  className="mt-1 w-24"
                  value={draft.priority}
                  onChange={(event) => setDraft({ ...draft, priority: Number(event.target.value) })}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={draft.is_active}
                  onChange={(event) => setDraft({ ...draft, is_active: event.target.checked })}
                />
                Active
              </label>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Conditions (all must match)</span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDraft({ ...draft, conditions: [...draft.conditions, { field: "", operator: "equals", value: "" }] })}
                >
                  <Plus className="h-3 w-3 mr-1" /> Add
                </Button>
              </div>
              <div className="mt-2 space-y-2">
                {draft.conditions.map((condition, index) => (
                  <div key={index} className="flex flex-wrap items-center gap-2">
                    <Input
                      placeholder="field (e.g. category)"
                      className="h-8 flex-1 min-w-32 text-sm"
                      value={condition.field}
                      onChange={(event) => setCondition(index, { field: event.target.value })}
                    />
                    <select
                      className="h-8 rounded-md border bg-background px-2 text-sm"
                      value={condition.operator}
                      onChange={(event) => setCondition(index, { operator: event.target.value })}
                    >
                      {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
                    </select>
                    <Input
                      placeholder="value"
                      className="h-8 flex-1 min-w-24 text-sm"
                      value={condition.value}
                      onChange={(event) => setCondition(index, { value: event.target.value })}
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => setDraft({ ...draft, conditions: draft.conditions.filter((_, i) => i !== index) })}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Actions</span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDraft({ ...draft, actions: [...draft.actions, { type: "notify", target: "" }] })}
                >
                  <Plus className="h-3 w-3 mr-1" /> Add
                </Button>
              </div>
              <div className="mt-2 space-y-2">
                {draft.actions.map((action, index) => (
                  <div key={index} className="flex flex-wrap items-center gap-2">
                    <select
                      className="h-8 rounded-md border bg-background px-2 text-sm"
                      value={action.type}
                      onChange={(event) => setAction(index, { type: event.target.value })}
                    >
                      {ACTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                    </select>
                    <Input
                      placeholder="target (e.g. #alerts, PROJ)"
                      className="h-8 flex-1 min-w-32 text-sm"
                      value={action.target}
                      onChange={(event) => setAction(index, { target: event.target.value })}
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => setDraft({ ...draft, actions: draft.actions.filter((_, i) => i !== index) })}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <Button size="sm" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save rule"}</Button>
              <Button size="sm" variant="ghost" disabled={busy} onClick={() => { setDraft(null); setStatus({ tone: "idle", message: "" }); }}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">Rules</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {rules.length === 0 ? (
            <p className="text-sm text-muted-foreground">No rules yet. Create one with “New Rule”.</p>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => (
                <div key={rule.rule_id} className="flex items-start justify-between gap-3 border-b pb-3 last:border-0">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{rule.name}</p>
                    <p className="text-xs text-muted-foreground">{summarize(rule)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">priority {rule.priority}</Badge>
                    <Badge variant={rule.is_active ? "success" : "secondary"}>{rule.is_active ? "Active" : "Inactive"}</Badge>
                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => remove(rule.rule_id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Conflict Resolution</CardTitle></CardHeader>
        <CardContent>
          <div className="text-xs space-y-1 text-muted-foreground">
            <p>1. <strong>Priority</strong> — higher priority rules win</p>
            <p>2. <strong>Specificity</strong> — more conditions = more specific</p>
            <p>3. <strong>Action-type dedupe</strong> — one action per type per insight</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
