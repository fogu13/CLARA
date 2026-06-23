import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/contexts/AuthContext";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Plus, Key, Trash2, Eye, EyeOff, Copy, CheckCircle2,
  AlertCircle, Zap, RefreshCw, ExternalLink,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";

// ─── Integration Catalog ─────────────────────────────────────────────────────

type IntegrationDef = {
  tool_type: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  fields: { key: string; label: string; type?: string; placeholder?: string }[];
  docsUrl?: string;
};

const CATALOG: IntegrationDef[] = [
  // CRM
  {
    tool_type: "hubspot",
    name: "HubSpot",
    description: "Sync contacts, deals, and feedback from your HubSpot CRM.",
    icon: "🟠",
    category: "CRM",
    fields: [
      { key: "api_key", label: "Private App Token", type: "password", placeholder: "pat-na1-..." },
      { key: "portal_id", label: "Portal ID", placeholder: "12345678" },
    ],
    docsUrl: "https://developers.hubspot.com/docs/api/private-apps",
  },
  {
    tool_type: "salesforce",
    name: "Salesforce",
    description: "Pull opportunities, cases, and contact data from Salesforce.",
    icon: "☁️",
    category: "CRM",
    fields: [
      { key: "instance_url", label: "Instance URL", placeholder: "https://myorg.salesforce.com" },
      { key: "client_id", label: "Consumer Key", placeholder: "" },
      { key: "client_secret", label: "Consumer Secret", type: "password", placeholder: "" },
    ],
    docsUrl: "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest",
  },
  {
    tool_type: "pipedrive",
    name: "Pipedrive",
    description: "Import deals, activities, and contacts from Pipedrive.",
    icon: "🟢",
    category: "CRM",
    fields: [
      { key: "api_token", label: "API Token", type: "password", placeholder: "" },
    ],
    docsUrl: "https://developers.pipedrive.com/docs/api/v1",
  },
  // Marketing Automation
  {
    tool_type: "mailchimp",
    name: "Mailchimp",
    description: "Pull campaign stats, subscriber data and engagement signals.",
    icon: "🐒",
    category: "Marketing Automation",
    fields: [
      { key: "api_key", label: "API Key", type: "password", placeholder: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-us1" },
      { key: "server_prefix", label: "Server Prefix", placeholder: "us1" },
    ],
    docsUrl: "https://mailchimp.com/developer/marketing/api/root/",
  },
  {
    tool_type: "mautic",
    name: "Mautic",
    description: "Ingest contacts, form submissions, and campaign events from Mautic.",
    icon: "📧",
    category: "Marketing Automation",
    fields: [
      { key: "base_url", label: "Mautic URL", placeholder: "https://mautic.yoursite.com" },
      { key: "client_id", label: "Client ID", placeholder: "" },
      { key: "client_secret", label: "Client Secret", type: "password", placeholder: "" },
    ],
  },
  {
    tool_type: "klaviyo",
    name: "Klaviyo",
    description: "Sync email, SMS, and flow performance into the signal stream.",
    icon: "📬",
    category: "Marketing Automation",
    fields: [
      { key: "api_key", label: "Private API Key", type: "password", placeholder: "pk_..." },
    ],
    docsUrl: "https://developers.klaviyo.com/en/reference/api-overview",
  },
  // Support
  {
    tool_type: "zendesk",
    name: "Zendesk",
    description: "Stream support tickets, CSAT scores, and NPS from Zendesk.",
    icon: "🎧",
    category: "Support",
    fields: [
      { key: "subdomain", label: "Subdomain", placeholder: "yourcompany" },
      { key: "email", label: "Agent Email", placeholder: "agent@company.com" },
      { key: "api_token", label: "API Token", type: "password", placeholder: "" },
    ],
    docsUrl: "https://developer.zendesk.com/api-reference/",
  },
  {
    tool_type: "intercom",
    name: "Intercom",
    description: "Pull conversations, surveys, and contact events from Intercom.",
    icon: "💬",
    category: "Support",
    fields: [
      { key: "access_token", label: "Access Token", type: "password", placeholder: "" },
    ],
    docsUrl: "https://developers.intercom.com/docs/",
  },
  // Analytics
  {
    tool_type: "google_analytics",
    name: "Google Analytics",
    description: "Ingest pageview, conversion, and funnel data as quantitative signals.",
    icon: "📊",
    category: "Analytics",
    fields: [
      { key: "property_id", label: "GA4 Property ID", placeholder: "123456789" },
      { key: "service_account_json", label: "Service Account JSON", type: "password", placeholder: '{"type":"service_account",...}' },
    ],
    docsUrl: "https://developers.google.com/analytics/devguides/reporting/data/v1",
  },
  // Survey
  {
    tool_type: "typeform",
    name: "Typeform",
    description: "Pull form responses and NPS scores directly from Typeform.",
    icon: "📝",
    category: "Survey",
    fields: [
      { key: "api_token", label: "Personal Access Token", type: "password", placeholder: "tfp_..." },
    ],
    docsUrl: "https://www.typeform.com/developers/",
  },
];

const CATEGORIES = [...new Set(CATALOG.map((c) => c.category))];

// ─── Types ────────────────────────────────────────────────────────────────────

type Integration = {
  id: string;
  tool_type: string;
  name: string;
  config: Record<string, unknown>;
  enabled: boolean;
  connected_at: string;
  sync_status: string;
  sync_error?: string | null;
};

type ApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  description?: string | null;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function generateApiKey(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return "ok_" + Array.from(array).map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function hashKey(key: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(key);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const IntegrationsPage = () => {
  const { user } = useAuth();
  const qc = useQueryClient();
  const workspaceId = useWorkspaceId();

  // ── Integrations ──
  const { data: integrations = [], isLoading: intLoading } = useQuery({
    queryKey: ["integrations", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("integrations")
        .select("*")
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
      return (data ?? []) as Integration[];
    },
    enabled: !!workspaceId,
  });

  // ── API Keys ──
  const { data: apiKeys = [], isLoading: keysLoading } = useQuery({
    queryKey: ["api_keys", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("api_keys")
        .select("*")
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
      return (data ?? []) as ApiKey[];
    },
    enabled: !!workspaceId,
  });

  // ── Connect dialog state ──
  const [connectDef, setConnectDef] = useState<IntegrationDef | null>(null);
  const [connectFields, setConnectFields] = useState<Record<string, string>>({});
  const [showFields, setShowFields] = useState<Record<string, boolean>>({});

  const connectMutation = useMutation({
    mutationFn: async () => {
      if (!connectDef || !workspaceId) return;
      const { error } = await supabase.from("integrations").insert({
        workspace_id: workspaceId,
        tool_type: connectDef.tool_type,
        name: connectDef.name,
        config: connectFields,
        enabled: true,
        sync_status: "idle",
      });
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success(`${connectDef?.name} connected successfully`);
      qc.invalidateQueries({ queryKey: ["integrations", workspaceId] });
      setConnectDef(null);
      setConnectFields({});
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const disconnectMutation = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from("integrations").delete().eq("id", id).eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Integration disconnected");
      qc.invalidateQueries({ queryKey: ["integrations", workspaceId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const { error } = await supabase.from("integrations").update({ enabled }).eq("id", id).eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", workspaceId] }),
    onError: (e: Error) => toast.error(e.message),
  });

  // ── API Key dialog state ──
  const [showAddKey, setShowAddKey] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyDesc, setNewKeyDesc] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [deleteKeyId, setDeleteKeyId] = useState<string | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const createKeyMutation = useMutation({
    mutationFn: async () => {
      if (!workspaceId) return;
      const key = generateApiKey();
      const hash = await hashKey(key);
      const { error } = await supabase.from("api_keys").insert({
        workspace_id: workspaceId,
        name: newKeyName,
        description: newKeyDesc || null,
        key_prefix: key.slice(0, 12),
        key_hash: hash,
      });
      if (error) throw error;
      return key;
    },
    onSuccess: (key) => {
      setCreatedKey(key ?? null);
      setNewKeyName("");
      setNewKeyDesc("");
      qc.invalidateQueries({ queryKey: ["api_keys", workspaceId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteKeyMutation = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from("api_keys").delete().eq("id", id).eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("API key deleted");
      qc.invalidateQueries({ queryKey: ["api_keys", workspaceId] });
      setDeleteKeyId(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKeyId(id);
      setTimeout(() => setCopiedKeyId(null), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const connectedTypes = new Set(integrations.map((i) => i.tool_type));

  return (
    <AppLayout title="Integrations">
      <Tabs defaultValue="connectors">
        <TabsList className="mb-6">
          <TabsTrigger value="connectors">Connectors</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
        </TabsList>

        {/* ── Connectors Tab ── */}
        <TabsContent value="connectors" className="space-y-8">
          {/* Active connections */}
          {integrations.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
                Active Connections
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {integrations.map((int) => {
                  const def = CATALOG.find((d) => d.tool_type === int.tool_type);
                  return (
                    <div
                      key={int.id}
                      className={cn(
                        "rounded-lg border bg-card p-5 shadow-sm",
                        int.sync_status === "error" && "border-destructive/40"
                      )}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{def?.icon ?? "🔌"}</span>
                          <div>
                            <p className="text-sm font-semibold">{int.name}</p>
                            <p className="text-xs text-muted-foreground capitalize">{def?.category}</p>
                          </div>
                        </div>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px]",
                            int.enabled && int.sync_status !== "error"
                              ? "border-success/40 text-success"
                              : "border-muted text-muted-foreground"
                          )}
                        >
                          {int.sync_status === "error" ? "Error" : int.enabled ? "Connected" : "Paused"}
                        </Badge>
                      </div>
                      {int.sync_error && (
                        <p className="text-xs text-destructive bg-destructive/5 rounded p-2 mb-3">
                          {int.sync_error}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mb-4">
                        Connected {formatDistanceToNow(new Date(int.connected_at), { addSuffix: true })}
                      </p>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="flex-1 text-xs"
                          onClick={() => toggleMutation.mutate({ id: int.id, enabled: !int.enabled })}
                        >
                          {int.enabled ? "Pause" : "Resume"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => disconnectMutation.mutate(int.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
              <Separator className="mt-8" />
            </section>
          )}

          {/* Catalog by category */}
          {CATEGORIES.map((cat) => (
            <section key={cat}>
              <h2 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
                {cat}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {CATALOG.filter((d) => d.category === cat).map((def) => {
                  const isConnected = connectedTypes.has(def.tool_type);
                  return (
                    <div
                      key={def.tool_type}
                      className="rounded-lg border bg-card p-5 shadow-sm flex flex-col gap-3"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{def.icon}</span>
                          <div>
                            <p className="text-sm font-semibold">{def.name}</p>
                            {isConnected && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-success">
                                <CheckCircle2 className="h-2.5 w-2.5" /> Connected
                              </span>
                            )}
                          </div>
                        </div>
                        {def.docsUrl && (
                          <a
                            href={def.docsUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-muted-foreground hover:text-foreground"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{def.description}</p>
                      <Button
                        size="sm"
                        variant={isConnected ? "outline" : "default"}
                        className="mt-auto"
                        onClick={() => {
                          setConnectDef(def);
                          setConnectFields({});
                          setShowFields({});
                        }}
                      >
                        <Zap className="h-3.5 w-3.5 mr-1.5" />
                        {isConnected ? "Reconfigure" : "Connect"}
                      </Button>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </TabsContent>

        {/* ── API Keys Tab ── */}
        <TabsContent value="api-keys" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">User API Keys</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Generate keys to authenticate external services or scripts against this workspace.
              </p>
            </div>
            <Button size="sm" onClick={() => { setShowAddKey(true); setCreatedKey(null); }}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              New API Key
            </Button>
          </div>

          {keysLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : apiKeys.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <Key className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
              <p className="text-sm font-medium">No API keys yet</p>
              <p className="text-xs text-muted-foreground mt-1">Create a key to integrate external tools.</p>
            </div>
          ) : (
            <div className="rounded-lg border bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/30">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Name</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Key</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Created</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Last Used</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {apiKeys.map((key) => (
                    <tr key={key.id} className="hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">{key.name}</td>
                      <td className="px-4 py-3">
                        <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                          {key.key_prefix}••••••••••••
                        </code>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">
                        {formatDistanceToNow(new Date(key.created_at), { addSuffix: true })}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">
                        {key.last_used_at
                          ? formatDistanceToNow(new Date(key.last_used_at), { addSuffix: true })
                          : "Never"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeleteKeyId(key.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* ── Connect Dialog ── */}
      <Dialog open={!!connectDef} onOpenChange={(o) => !o && setConnectDef(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="text-2xl">{connectDef?.icon}</span>
              Connect {connectDef?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {connectDef?.fields.map((field) => (
              <div key={field.key}>
                <Label htmlFor={field.key}>{field.label}</Label>
                <div className="relative mt-1.5">
                  <Input
                    id={field.key}
                    type={field.type === "password" && !showFields[field.key] ? "password" : "text"}
                    placeholder={field.placeholder}
                    value={connectFields[field.key] ?? ""}
                    onChange={(e) =>
                      setConnectFields((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                    className={field.type === "password" ? "pr-10" : ""}
                  />
                  {field.type === "password" && (
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      onClick={() =>
                        setShowFields((prev) => ({ ...prev, [field.key]: !prev[field.key] }))
                      }
                    >
                      {showFields[field.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {connectDef?.docsUrl && (
              <a
                href={connectDef.docsUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                View {connectDef.name} API docs
              </a>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConnectDef(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => connectMutation.mutate()}
              disabled={connectMutation.isPending}
            >
              {connectMutation.isPending ? (
                <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Zap className="h-3.5 w-3.5 mr-1.5" />
              )}
              Connect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Add API Key Dialog ── */}
      <Dialog open={showAddKey} onOpenChange={(o) => { if (!o) { setShowAddKey(false); setCreatedKey(null); } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New API Key</DialogTitle>
          </DialogHeader>
          {createdKey ? (
            <div className="space-y-4 py-2">
              <div className="rounded-lg bg-success/10 border border-success/30 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  <p className="text-sm font-semibold text-success">Key created — save it now</p>
                </div>
                <p className="text-xs text-muted-foreground mb-3">
                  This key will only be shown once. Store it somewhere safe.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded bg-muted px-3 py-2 text-xs font-mono break-all">
                    {createdKey}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(createdKey, "new")}
                  >
                    {copiedKeyId === "new" ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <div>
                <Label htmlFor="key-name">Key Name</Label>
                <Input
                  id="key-name"
                  className="mt-1.5"
                  placeholder="e.g. Zapier webhook"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="key-desc">Description (optional)</Label>
                <Input
                  id="key-desc"
                  className="mt-1.5"
                  placeholder="What will this key be used for?"
                  value={newKeyDesc}
                  onChange={(e) => setNewKeyDesc(e.target.value)}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            {createdKey ? (
              <Button onClick={() => { setShowAddKey(false); setCreatedKey(null); }}>Done</Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setShowAddKey(false)}>Cancel</Button>
                <Button
                  onClick={() => createKeyMutation.mutate()}
                  disabled={!newKeyName.trim() || createKeyMutation.isPending}
                >
                  {createKeyMutation.isPending ? (
                    <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Key className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  Generate Key
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Key Confirm ── */}
      <AlertDialog open={!!deleteKeyId} onOpenChange={(o) => !o && setDeleteKeyId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete API Key?</AlertDialogTitle>
            <AlertDialogDescription>
              Any services using this key will immediately lose access. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteKeyId && deleteKeyMutation.mutate(deleteKeyId)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppLayout>
  );
};

export default IntegrationsPage;
