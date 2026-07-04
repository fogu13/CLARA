"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { getSystemConfig, getWorkspace, updateWorkspace } from "@/lib/client-api";
import type { SystemConfig, WorkspaceSettings } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const DEFAULTS: WorkspaceSettings = {
  name: "My Workspace",
  slug: "my-workspace",
  notification_email: "",
  measurement_window_days: 14,
  learning_half_life_days: 180
};

type Status = { tone: "idle" | "busy" | "ok" | "error"; message: string };

export default function SettingsPage() {
  const { t } = useI18n();
  const [settings, setSettings] = useState<WorkspaceSettings>(DEFAULTS);
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [status, setStatus] = useState<Status>({ tone: "idle", message: "" });

  const [workspaceLoadFailed, setWorkspaceLoadFailed] = useState(false);

  useEffect(() => {
    // If the load fails, saving would overwrite real workspace data with the
    // placeholder defaults; disable Save until a real read succeeds.
    getWorkspace()
      .then((data) => {
        setSettings(data);
        setWorkspaceLoadFailed(false);
      })
      .catch(() => setWorkspaceLoadFailed(true));
    getSystemConfig().then(setConfig).catch(() => {});
  }, []);

  function update<K extends keyof WorkspaceSettings>(key: K, value: WorkspaceSettings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    setStatus({ tone: "busy", message: t.settings.saving });
    try {
      setSettings(await updateWorkspace(settings));
      setStatus({ tone: "ok", message: t.settings.saved });
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : t.settings.saveFailed });
    }
  }

  const busy = status.tone === "busy";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.settings.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t.settings.subtitle}</p>
        {workspaceLoadFailed ? (
          <p role="alert" className="mt-2 rounded-md border border-destructive/50 px-3 py-2 text-sm text-destructive">
            {t.common.error}
          </p>
        ) : null}
      </div>

      {status.message ? (
        <div
          className={`rounded-md border p-3 text-sm ${
            status.tone === "error"
              ? "border-destructive/40 bg-destructive/5 text-destructive"
              : status.tone === "ok"
                ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
                : "border-border bg-muted text-muted-foreground"
          }`}
        >
          {status.message}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t.settings.workspace}</CardTitle>
          <CardDescription>{t.settings.workspaceSubtitle}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="name">{t.settings.workspaceName}</Label>
            <Input
              id="name"
              className="mt-1"
              value={settings.name}
              onChange={(event) => update("name", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="slug">{t.settings.slug}</Label>
            <Input
              id="slug"
              className="mt-1"
              value={settings.slug}
              onChange={(event) => update("slug", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="email">{t.settings.notificationEmail}</Label>
            <Input
              id="email"
              type="email"
              className="mt-1"
              placeholder="alerts@company.com"
              value={settings.notification_email}
              onChange={(event) => update("notification_email", event.target.value)}
            />
          </div>
          <Button onClick={save} disabled={busy || workspaceLoadFailed}>
            {busy ? t.settings.saving : t.settings.saveChanges}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.settings.measurement}</CardTitle>
          <CardDescription>{t.settings.measurementSubtitle}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="window">{t.settings.windowDays}</Label>
            <Input
              id="window"
              type="number"
              className="mt-1"
              value={settings.measurement_window_days}
              onChange={(event) => {
                // Don't coerce an empty field to 0 (Number("") === 0); leave it unchanged.
                if (event.target.value !== "") update("measurement_window_days", Number(event.target.value));
              }}
            />
          </div>
          <div>
            <Label htmlFor="half-life">{t.settings.halfLifeDays}</Label>
            <Input
              id="half-life"
              type="number"
              className="mt-1"
              value={settings.learning_half_life_days}
              onChange={(event) => {
                if (event.target.value !== "") update("learning_half_life_days", Number(event.target.value));
              }}
            />
          </div>
          <Button onClick={save} disabled={busy || workspaceLoadFailed}>
            {busy ? t.settings.saving : t.settings.saveChanges}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.settings.aiConfig}</CardTitle>
          <CardDescription>{t.settings.aiConfigSubtitle}</CardDescription>
        </CardHeader>
        <CardContent>
          {config ? (
            <div className="grid gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">AI_BASE_URL</span>
                <code className="bg-muted px-2 py-0.5 rounded">{config.ai_base_url}</code>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">AI_MODEL</span>
                <code className="bg-muted px-2 py-0.5 rounded">{config.ai_model}</code>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t.settings.authLabel}</span>
                <code className="bg-muted px-2 py-0.5 rounded">{config.auth_enabled ? t.compliance.enabled : "disabled"}</code>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t.compliance.configUnavailable}</p>
          )}
          <p className="text-xs text-muted-foreground mt-3">
            {t.settings.aiConfigNote}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
