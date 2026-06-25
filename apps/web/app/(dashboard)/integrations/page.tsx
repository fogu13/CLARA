"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { apiHeaders } from "@/lib/client-api";
import { Plug, Trash2, CheckCircle, Loader2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ConnectorConfig {
  connector_type: string;
  config: Record<string, any>;
  display_name: string;
  is_active: boolean;
}

const CONNECTOR_CATALOG = [
  {
    type: "zendesk",
    name: "Zendesk",
    category: "Source (Pull)",
    description: "Pull support tickets as customer feedback signals",
    fields: [
      { key: "subdomain", label: "Subdomain", placeholder: "company" },
      { key: "email", label: "Email", placeholder: "user@company.com" },
      { key: "api_token", label: "API Token", placeholder: "..." },
    ],
  },
  {
    type: "jira",
    name: "Jira",
    category: "Destination (Push)",
    description: "Create issues from approved actions",
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
    description: "Post notifications to channels on approved actions",
    fields: [
      { key: "bot_token", label: "Bot Token", placeholder: "xoxb-..." },
      { key: "channel", label: "Channel", placeholder: "#customer-feedback" },
    ],
  },
];

export default function IntegrationsPage() {
  const [connectors, setConnectors] = useState<ConnectorConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingConnector, setEditingConnector] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    loadConnectors();
  }, []);

  async function loadConnectors() {
    try {
      const res = await fetch(`${API_URL}/connectors`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        setConnectors(data);
      }
    } catch {
      // API not running — show empty state
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
      // editable inputs — leave them blank so the operator re-enters to change them.
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
      await fetch(`${API_URL}/connectors/${editingConnector}`, {
        method: "PUT",
        headers: apiHeaders(),
        body: JSON.stringify(formData),
      });
      await loadConnectors();
      setEditingConnector(null);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  }

  async function deleteConnector(type: string) {
    await fetch(`${API_URL}/connectors/${type}`, { method: "DELETE", headers: apiHeaders() });
    await loadConnectors();
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
      if (data.status === "ok") {
        setTestResult("success");
      } else {
        setTestResult(`error: ${data.message}`);
      }
    } catch (e) {
      setTestResult(`error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setTesting(false);
    }
  }

  async function pullZendesk() {
    try {
      const res = await fetch(`${API_URL}/connectors/zendesk/pull`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify({}),
      });
      const data = await res.json();
      alert(`Pulled ${data.pulled} signals from Zendesk`);
    } catch (e) {
      alert(`Pull failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  }

  if (loading) return <div className="text-muted-foreground">Loading connectors...</div>;

  const categories = ["Source (Pull)", "Destination (Push)"];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure source and destination connectors to close the feedback loop
        </p>
      </div>

      <Tabs value="connectors">
        <TabsList>
          <TabsTrigger value="connectors">Connectors</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
        </TabsList>

        <TabsContent value="connectors" className="space-y-4">
          {categories.map(category => (
            <div key={category}>
              <h2 className="text-sm font-semibold text-muted-foreground mb-3">{category}</h2>
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
                              Connected
                            </Badge>
                          ) : (
                            <Badge variant="outline">Not configured</Badge>
                          )}
                        </div>
                        <CardDescription>{connector.description}</CardDescription>
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
                                {testResult === "success" ? "Connection successful!" : testResult}
                              </div>
                            )}
                            <div className="flex gap-2">
                              <Button size="sm" onClick={saveConnector} disabled={saving}>
                                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : "Save"}
                              </Button>
                              <Button size="sm" variant="outline" onClick={testConnector} disabled={testing}>
                                {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : "Test"}
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setEditingConnector(null)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {configured && connector.type === "zendesk" && (
                              <Button size="sm" variant="outline" onClick={pullZendesk}>
                                Pull Tickets
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
              <CardTitle>API Keys</CardTitle>
              <CardDescription>Keys for programmatic API access</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                API key management will be available in Phase 6 (SaaS readiness).
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
