"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { apiBaseUrl, apiHeaders, getSystemConfig, getWorkspace, updateWorkspace } from "@/lib/client-api";
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
  const [aiUrl, setAiUrl] = useState("");
  const [aiModel, setAiModel] = useState("");
  const [aiEmbedModel, setAiEmbedModel] = useState("");
  const [aiKey, setAiKey] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  async function saveAi() {
    setAiBusy(true);
    setAiStatus(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/settings/ai`, {
        method: "PUT",
        headers: apiHeaders(),
        body: JSON.stringify({ base_url: aiUrl, model: aiModel, embed_model: aiEmbedModel, api_key: aiKey }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail ?? `Save failed (${res.status})`);
      setAiKey("");
      setAiStatus(
        data?.warning
          ? { tone: "error", text: data.warning }
          : { tone: "ok", text: t.settings.aiSaved }
      );
      getSystemConfig().then(setConfig).catch(() => {});
    } catch (e) {
      setAiStatus({ tone: "error", text: e instanceof Error ? e.message : "Save failed" });
    } finally {
      setAiBusy(false);
    }
  }

  async function testAi() {
    setAiBusy(true);
    setAiStatus(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/settings/ai/test`, { method: "POST", headers: apiHeaders() });
      const data = await res.json().catch(() => null);
      if (data?.ok && data?.embed_ok === false)
        setAiStatus({ tone: "error", text: `${t.settings.aiTestEmbedFail} ${data.embed_error ?? data.embed_model}` });
      else if (data?.ok) setAiStatus({ tone: "ok", text: `${t.settings.aiTestOk} (${data.model})` });
      else setAiStatus({ tone: "error", text: `${t.settings.aiTestFail} ${data?.error ?? res.status}` });
    } catch (e) {
      setAiStatus({ tone: "error", text: e instanceof Error ? e.message : "Test failed" });
    } finally {
      setAiBusy(false);
    }
  }

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
        <CardContent className="space-y-4">
          {config ? (
            <div className="flex flex-wrap gap-4 text-sm">
              <span className="text-muted-foreground">
                {t.settings.authLabel}: <code className="rounded bg-muted px-2 py-0.5">{config.auth_enabled ? t.compliance.enabled : "disabled"}</code>
              </span>
              <span className="text-muted-foreground">
                Aktiv: <code className="rounded bg-muted px-2 py-0.5">{config.ai_model}</code> @ <code className="rounded bg-muted px-2 py-0.5">{config.ai_base_url}</code>
              </span>
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="ai-url">{t.settings.aiBaseUrl}</Label>
            <Input id="ai-url" value={aiUrl} onChange={(e) => setAiUrl(e.target.value)} placeholder="https://api.mistral.ai/v1 · http://localhost:11434/v1" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ai-model">{t.settings.aiModel}</Label>
            <Input id="ai-model" value={aiModel} onChange={(e) => setAiModel(e.target.value)} placeholder="mistral-small-latest · qwen3:32b" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ai-embed-model">{t.settings.aiEmbedModel}</Label>
            <Input id="ai-embed-model" value={aiEmbedModel} onChange={(e) => setAiEmbedModel(e.target.value)} placeholder="mistral-embed · nomic-embed-text" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ai-key">{t.settings.aiApiKey}</Label>
            <Input id="ai-key" type="password" value={aiKey} onChange={(e) => setAiKey(e.target.value)} placeholder="sk-…" />
          </div>
          <p className="text-xs text-muted-foreground">
            {t.settings.aiPresets}{" "}
            <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => { setAiUrl("https://api.mistral.ai/v1"); setAiModel("mistral-small-latest"); setAiEmbedModel("mistral-embed"); }}>Mistral (EU)</button>
            {" · "}
            <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => { setAiUrl("http://localhost:11434/v1"); setAiModel("qwen3:32b"); setAiEmbedModel("nomic-embed-text"); }}>Ollama (local)</button>
            {" · "}
            <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => { setAiUrl("https://opencode.ai/zen/v1"); setAiModel("glm-5.2"); setAiEmbedModel("gemini-embedding-001"); }}>OpenCode Zen</button>
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={saveAi} disabled={aiBusy}>
              {aiBusy ? t.settings.saving : t.settings.saveChanges}
            </Button>
            <Button size="sm" variant="outline" onClick={testAi} disabled={aiBusy}>
              {aiBusy ? t.settings.aiTesting : t.settings.aiTest}
            </Button>
          </div>
          {aiStatus ? (
            <p role="status" className={`text-sm ${aiStatus.tone === "ok" ? "text-emerald-600" : "text-destructive"}`}>
              {aiStatus.text}
            </p>
          ) : null}
          <p className="text-xs text-muted-foreground">{t.settings.aiConfigNote}</p>
        </CardContent>
      </Card>
    </div>
  );
}
