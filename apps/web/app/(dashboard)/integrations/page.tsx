"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { apiBaseUrl, apiHeaders } from "@/lib/client-api";
import { Plug, Trash2, CheckCircle, Loader2 } from "lucide-react";
import { useI18n } from "@/lib/i18n";

const API_URL = apiBaseUrl();

interface ConnectorConfig {
  connector_type: string;
  config: Record<string, any>;
  display_name: string;
  is_active: boolean;
}

const PULL_SOURCES = ["zendesk", "app_store", "trustpilot", "google_play", "google_business"];

const CONNECTOR_CATALOG = [
  {
    type: "zendesk",
    name: "Zendesk",
    category: "Source (Pull)",
    descKey: "descZendesk" as const,
    fields: [
      { key: "subdomain", label: "Subdomain", placeholder: "company" },
      { key: "email", label: "Email", placeholder: "user@company.com" },
      { key: "api_token", label: "API Token", placeholder: "..." },
    ],
  },
  {
    type: "app_store",
    name: "App Store Reviews",
    category: "Source (Pull)",
    descKey: "descAppStore" as const,
    fields: [
      { key: "app_id", label: "App Store ID", placeholder: "1279625243" },
      { key: "countries", label: "Countries (comma-separated)", placeholder: "de,at,ch" },
    ],
  },
  {
    type: "trustpilot",
    name: "Trustpilot",
    category: "Source (Pull)",
    descKey: "descTrustpilot" as const,
    fields: [
      { key: "api_key", label: "API Key", placeholder: "your Trustpilot Business API key" },
      { key: "business_unit_id", label: "Business Unit ID", placeholder: "46d5a5..." },
    ],
  },
  {
    type: "google_play",
    name: "Google Play Reviews",
    category: "Source (Pull)",
    descKey: "descGooglePlay" as const,
    fields: [
      { key: "package_name", label: "Package Name", placeholder: "com.example.app" },
      { key: "service_account_json", label: "Service Account JSON", placeholder: "paste the full key JSON" },
    ],
  },
  {
    type: "google_business",
    name: "Google Reviews",
    category: "Source (Pull)",
    descKey: "descGoogleBusiness" as const,
    fields: [
      { key: "client_id", label: "OAuth Client ID", placeholder: "....apps.googleusercontent.com" },
      { key: "client_secret", label: "OAuth Client Secret", placeholder: "GOCSPX-..." },
      { key: "refresh_token", label: "Refresh Token", placeholder: "1//..." },
      { key: "account_id", label: "Account ID", placeholder: "1234567890" },
      { key: "location_id", label: "Location ID", placeholder: "9876543210" },
    ],
  },
  {
    type: "webhook",
    name: "Webhook",
    category: "Source (Pull)",
    descKey: "descWebhook" as const,
    fields: [
      { key: "secret", label: "Shared Secret (HMAC-SHA256)", placeholder: "generate a long random string" },
    ],
  },
  {
    type: "jira",
    name: "Jira",
    category: "Destination (Push)",
    descKey: "descJira" as const,
    fields: [
      { key: "base_url", label: "Base URL", placeholder: "https://company.atlassian.net" },
      { key: "email", label: "Email", placeholder: "user@company.com" },
      { key: "api_token", label: "API Token", placeholder: "..." },
      { key: "project_key", label: "Project Key", placeholder: "PROJ" },
    ],
  },
  {
    type: "slack",
    name: "Slack",
    category: "Destination (Push)",
    descKey: "descSlack" as const,
    fields: [
      { key: "bot_token", label: "Bot Token", placeholder: "xoxb-..." },
      { key: "channel", label: "Channel", placeholder: "#customer-feedback" },
    ],
  },
];

export default function IntegrationsPage() {
  const { t } = useI18n();
  const [connectors, setConnectors] = useState<ConnectorConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingConnector, setEditingConnector] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [apiKeysList, setApiKeysList] = useState<Array<{ id: number; name: string; role: string; key_prefix: string; revoked_at: string | null }>>([]);
  const [keyName, setKeyName] = useState("");
  const [keyRole, setKeyRole] = useState("viewer");
  const [keyBusy, setKeyBusy] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);

  useEffect(() => {
    loadConnectors();
    loadApiKeys();
  }, []);

  async function loadApiKeys() {
    try {
      const res = await fetch(`${API_URL}/api-keys`, { headers: apiHeaders() });
      if (res.ok) setApiKeysList(await res.json());
    } catch {
      // keys panel degrades silently; connector load errors already surface
    }
  }

  async function createKey() {
    setKeyBusy(true);
    try {
      const res = await fetch(`${API_URL}/api-keys`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify({ name: keyName, role: keyRole }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail ?? `Create failed (${res.status})`);
      setNewKey(data.key);
      setKeyName("");
      await loadApiKeys();
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : "Create failed" });
    } finally {
      setKeyBusy(false);
    }
  }

  async function revokeKey(id: number, name: string) {
    if (!window.confirm(`Revoke API key "${name}"? Requests using it will stop working immediately.`)) return;
    try {
      const res = await fetch(`${API_URL}/api-keys/${id}`, { method: "DELETE", headers: apiHeaders() });
      if (!res.ok) throw new Error(`Revoke failed (${res.status})`);
      setNewKey(null);
      await loadApiKeys();
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : "Revoke failed" });
    }
  }

  async function loadConnectors() {
    try {
      const res = await fetch(`${API_URL}/connectors`, { headers: apiHeaders() });
      if (res.ok) {
        setConnectors(await res.json());
        setLoadError(null);
      } else {
        // A 403/500 must not masquerade as "nothing configured".
        setLoadError(`Couldn't load connectors (${res.status}).`);
      }
    } catch {
      setLoadError("API unreachable. Connector status unknown.");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(connectorType: string) {
    const existing = connectors.find(c => c.connector_type === connectorType);
    const fields = CONNECTOR_CATALOG.find(c => c.type === connectorType)?.fields || [];
    const initial: Record<string, string> = {};
    fields.forEach(f => {
      // The API masks secret values as "***redacted***"; never hydrate those into
      // editable inputs; leave them blank so the operator re-enters to change them.
      const value = existing?.config[f.key];
      initial[f.key] = !value || value === "***redacted***" ? "" : value;
    });
    setFormData(initial);
    setEditingConnector(connectorType);
    setTestResult(null);
  }

  async function saveConnector() {
    if (!editingConnector) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/connectors/${editingConnector}`, {
        method: "PUT",
        headers: apiHeaders(),
        body: JSON.stringify(formData),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? `Save failed (${res.status})`);
      }
      await loadConnectors();
      setEditingConnector(null);
    } catch (e) {
      // Previously swallowed: a failed save (e.g. 403 for non-admins) looked successful.
      setNotice({ tone: "error", text: `Save failed: ${e instanceof Error ? e.message : "unknown"}` });
    } finally {
      setSaving(false);
    }
  }

  async function deleteConnector(type: string) {
    if (!window.confirm(`Delete the ${type} connector configuration?`)) return;
    try {
      const res = await fetch(`${API_URL}/connectors/${type}`, { method: "DELETE", headers: apiHeaders() });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? `Delete failed (${res.status})`);
      }
      await loadConnectors();
      setNotice({ tone: "ok", text: `${type} connector deleted.` });
    } catch (e) {
      setNotice({ tone: "error", text: `Delete failed: ${e instanceof Error ? e.message : "unknown"}` });
    }
  }

  async function testConnector() {
    if (!editingConnector) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_URL}/connectors/test/${editingConnector}`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      if (data?.status === "ok") {
        setTestResult("success");
      } else {
        setTestResult(`error: ${data?.message ?? data?.detail ?? `test failed (${res.status})`}`);
      }
    } catch (e) {
      setTestResult(`error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setTesting(false);
    }
  }

  async function pullSource(connectorType: string) {
    try {
      const res = await fetch(`${API_URL}/connectors/${connectorType}/pull`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify({}),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Pull failed (${res.status})`);
      }
      setNotice({ tone: "ok", text: `Pulled ${data.pulled} signals (${data.imported} new, ${data.skipped_duplicates} duplicates)` });
    } catch (e) {
      setNotice({ tone: "error", text: `Pull failed: ${e instanceof Error ? e.message : "unknown"}` });
    }
  }

  if (loading) return <div className="text-muted-foreground">Loading connectors...</div>;

  const categories = ["Source (Pull)", "Destination (Push)"];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.integrations.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t.integrations.subtitle}
        </p>
      </div>

      {notice ? (
        <div className={`rounded-md border px-3 py-2 text-sm ${notice.tone === "ok" ? "border-emerald-300 text-emerald-700" : "border-destructive text-destructive"}`}>
          {notice.text}
        </div>
      ) : null}
      {loadError ? (
        <div className="rounded-md border border-amber-300 px-3 py-2 text-sm text-amber-700">{loadError}</div>
      ) : null}

      <Tabs value="connectors">
        <TabsList>
          <TabsTrigger value="connectors">{t.integrations.connectors}</TabsTrigger>
          <TabsTrigger value="api-keys">{t.integrations.apiKeys}</TabsTrigger>
        </TabsList>

        <TabsContent value="connectors" className="space-y-4">
          {categories.map(category => (
            <div key={category}>
              <h2 className="text-sm font-semibold text-muted-foreground mb-3">{category === "Source (Pull)" ? t.integrations.sourcePull : t.integrations.destinationPush}</h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {CONNECTOR_CATALOG.filter(c => c.category === category).map(connector => {
                  const configured = connectors.find(c => c.connector_type === connector.type);
                  const isEditing = editingConnector === connector.type;
                  return (
                    <Card key={connector.type}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Plug className="h-5 w-5 text-primary" />
                            <CardTitle className="text-base">{connector.name}</CardTitle>
                          </div>
                          {configured ? (
                            <Badge variant="success">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              {t.integrations.connected}
                            </Badge>
                          ) : (
                            <Badge variant="outline">{t.integrations.notConfigured}</Badge>
                          )}
                        </div>
                        <CardDescription>{t.integrations[connector.descKey]}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {isEditing ? (
                          <div className="space-y-3">
                            {connector.fields.map(field => (
                              <div key={field.key}>
                                <Label className="text-xs">{field.label}</Label>
                                <Input
                                  className="mt-1 h-8 text-sm"
                                  placeholder={field.placeholder}
                                  value={formData[field.key] || ""}
                                  onChange={e => setFormData({ ...formData, [field.key]: e.target.value })}
                                />
                              </div>
                            ))}
                            {testResult && (
                              <div className={`text-xs ${testResult === "success" ? "text-emerald-600" : "text-destructive"}`}>
                                {testResult === "success" ? t.integrations.connectionOk : testResult}
                              </div>
                            )}
                            <div className="flex gap-2">
                              <Button size="sm" onClick={saveConnector} disabled={saving}>
                                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : t.common.save}
                              </Button>
                              {editingConnector !== "webhook" && (
                              <Button size="sm" variant="outline" onClick={testConnector} disabled={testing}>
                                {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : t.integrations.test}
                              </Button>)}
                              <Button size="sm" variant="ghost" onClick={() => setEditingConnector(null)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {configured && PULL_SOURCES.includes(connector.type) && (
                              <Button size="sm" variant="outline" onClick={() => pullSource(connector.type)}>
                                {t.integrations.pullNow}
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant={configured ? "ghost" : "default"}
                              onClick={() => startEdit(connector.type)}
                            >
                              {configured ? "Edit" : "Connect"}
                            </Button>
                            {configured && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-destructive ml-2"
                                onClick={() => deleteConnector(connector.type)}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="api-keys">
          <Card>
            <CardHeader>
              <CardTitle>{t.integrations.apiKeys}</CardTitle>
              <CardDescription>{t.integrations.apiKeysHint}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {newKey ? (
                <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm">
                  <p className="font-medium text-emerald-800">{t.integrations.keyCreatedOnce}</p>
                  <code className="mt-1 block select-all break-all rounded bg-white px-2 py-1 text-xs">{newKey}</code>
                  <p className="mt-2 text-xs text-emerald-700">{t.integrations.keyUsage}</p>
                </div>
              ) : null}

              <div className="flex flex-wrap items-end gap-2">
                <div>
                  <Label htmlFor="key-name">{t.integrations.keyName}</Label>
                  <Input id="key-name" value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="bi-export" className="w-48" />
                </div>
                <div>
                  <Label htmlFor="key-role">{t.integrations.keyRole}</Label>
                  <select
                    id="key-role"
                    value={keyRole}
                    onChange={(e) => setKeyRole(e.target.value)}
                    className="block h-10 rounded-md border bg-background px-3 text-sm"
                  >
                    <option value="viewer">viewer</option>
                    <option value="editor">editor</option>
                    <option value="admin">admin</option>
                  </select>
                </div>
                <Button size="sm" onClick={createKey} disabled={keyBusy}>
                  {t.integrations.createKey}
                </Button>
              </div>

              {apiKeysList.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t.integrations.noKeys}</p>
              ) : (
                <div className="space-y-2">
                  {apiKeysList.map((key) => (
                    <div key={key.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <div className="min-w-0">
                        <span className="font-medium">{key.name}</span>
                        <span className="ml-2 text-xs text-muted-foreground">{key.key_prefix}… · {key.role}</span>
                        {key.revoked_at ? (
                          <Badge variant="outline" className="ml-2">{t.integrations.revokedLabel}</Badge>
                        ) : null}
                      </div>
                      {!key.revoked_at ? (
                        <Button size="sm" variant="ghost" onClick={() => revokeKey(key.id, key.name)}>
                          {t.integrations.revokeKey}
                        </Button>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
