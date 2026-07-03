"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, FileText, AlertTriangle, CheckCircle, Download, Cpu, Globe, UserX } from "lucide-react";
import { apiBaseUrl, apiHeaders, getSystemConfig } from "@/lib/client-api";
import type { SystemConfig } from "@/lib/types";

export default function CompliancePage() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    getSystemConfig().then(setConfig).catch(() => {});
  }, []);

  async function downloadAuditLog() {
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/audit-export`, { headers: apiHeaders() });
      if (!res.ok) throw new Error(`Export failed (${res.status}) — admin role required`);
      const blob = new Blob([JSON.stringify(await res.json(), null, 2)], {
        type: "application/json"
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `clara-audit-export-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  const aiHost = (() => {
    try {
      return config ? new URL(config.ai_base_url).host : null;
    } catch {
      return config?.ai_base_url ?? null;
    }
  })();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Compliance</h1>
          <p className="text-sm text-muted-foreground mt-1">
            EU AI Act + GDPR assessment for customer feedback AI processing
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button onClick={() => void downloadAuditLog()} disabled={exporting}>
            <Download className="mr-1 h-4 w-4" />
            {exporting ? "Exporting…" : "Download audit log"}
          </Button>
          {exportError ? <p className="text-xs text-destructive">{exportError}</p> : null}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm text-muted-foreground">Overall Score</CardTitle>
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">87</div>
            <p className="text-xs text-muted-foreground mt-1">out of 100</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">GDPR</CardTitle></CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">92</div>
            <p className="text-xs text-muted-foreground mt-1">Lawful basis + data minimization</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">EU AI Act</CardTitle></CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">82</div>
            <p className="text-xs text-muted-foreground mt-1">Transparency + human oversight</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Cpu className="h-4 w-4" /> Model card</CardTitle>
            <CardDescription>Live configuration of the AI layer — read from the running API</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {config ? (
              <>
                <div className="flex justify-between"><span className="text-muted-foreground">Model</span><code className="bg-muted px-2 py-0.5 rounded">{config.ai_model}</code></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Inference endpoint</span><code className="bg-muted px-2 py-0.5 rounded">{aiHost}</code></div>
                <div className="flex justify-between"><span className="text-muted-foreground">API authentication</span><Badge variant={config.auth_enabled ? "success" : "warning"}>{config.auth_enabled ? "enabled" : "disabled (dev)"}</Badge></div>
              </>
            ) : (
              <p className="text-muted-foreground">System config unavailable.</p>
            )}
            <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
              <li>• Purpose: classify + summarize customer feedback; propose (never execute) actions.</li>
              <li>• Provider-agnostic (OpenAI-compatible): routable to EU-hosted or fully local models (Ollama/vLLM).</li>
              <li>• No fine-tuning on customer data — adaptation via retrieval, taxonomy and outcome learnings.</li>
              <li>• Every AI output carries confidence, evidence links and stated limitations.</li>
              <li>• Known limitations: non-deterministic outputs; quality tracked by a published eval harness.</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Globe className="h-4 w-4" /> Data residency</CardTitle>
            <CardDescription>Where customer data lives and what it never touches</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>Feedback, context and outcomes stay in the deployment&apos;s own database (local-first SQLite or your EU Postgres).</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>No external analytics vendor: product metrics are stored in the same database, nowhere else.</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>Inference endpoint is configurable per deployment — EU-hosted or on-premise; visible in the model card.</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>Outbound connectors (Jira/Slack/Zendesk) receive only the drafted action content a human approved.</span></div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><UserX className="h-4 w-4" /> Data-subject rights (GDPR Art. 17 / Art. 20)</CardTitle>
          <CardDescription>Built into the product — no support ticket required</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="rounded-md border p-3">
            <p className="font-medium">Export (portability, Art. 20)</p>
            <code className="mt-1 block text-xs bg-muted rounded px-2 py-1">GET /customers/&#123;customer_id&#125;/data-export</code>
            <p className="mt-1 text-xs text-muted-foreground">Returns every signal, journey event, context record and evidence appearance for one customer as JSON.</p>
          </div>
          <div className="rounded-md border p-3">
            <p className="font-medium">Erasure (right to be forgotten, Art. 17)</p>
            <code className="mt-1 block text-xs bg-muted rounded px-2 py-1">DELETE /customers/&#123;customer_id&#125;/data</code>
            <p className="mt-1 text-xs text-muted-foreground">
              Deletes signals, journey events and context; scrubs evidence excerpts inside draft problems.
              All-or-nothing: partial erasure is rejected. The erased identifier is not retained in telemetry.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compliance Assessment</CardTitle>
          <CardDescription>Key requirements for AI-powered customer feedback processing</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Human Oversight (Art 14)</p>
                <p className="text-xs text-muted-foreground">
                  Human-in-the-loop approval for all consequential actions. The pipeline
                  pauses at the approval interrupt before any external push.
                </p>
              </div>
              <Badge variant="success">Compliant</Badge>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Transparency (Art 50)</p>
                <p className="text-xs text-muted-foreground">
                  AI-generated content is labelled with audit metadata (model, source,
                  limitations). Users can see which insights are LLM-synthesized.
                </p>
              </div>
              <Badge variant="success">Compliant</Badge>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Data Minimization (GDPR Art 5)</p>
                <p className="text-xs text-muted-foreground">
                  PII redaction in learning conclusions. Pseudonymized identifiers for
                  reviewers. Customer feedback capped at 2000 chars for LLM context.
                </p>
              </div>
              <Badge variant="success">Compliant</Badge>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Data-Subject Rights (GDPR Art 17 / 20)</p>
                <p className="text-xs text-muted-foreground">
                  Per-customer export and erasure are product endpoints (see above), not a
                  manual process. Erasure is all-or-nothing and audit-safe.
                </p>
              </div>
              <Badge variant="success">Compliant</Badge>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Local-First Processing</p>
                <p className="text-xs text-muted-foreground">
                  Provider-agnostic AI layer supports Ollama/vLLM for on-premise processing.
                  No data leaves the EU when configured with local models.
                </p>
              </div>
              <Badge variant="success">Compliant</Badge>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Risk Classification (AI Act)</p>
                <p className="text-xs text-muted-foreground">
                  Documented assessment: text-based feedback triage with human approval is
                  minimal/limited risk — not an Annex III use case. See docs/eu-ai-act-mapping.md.
                </p>
              </div>
              <Badge variant="success">Documented</Badge>
            </div>

            <div className="flex items-start gap-3">
              <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm font-medium">DPIA Documentation</p>
                <p className="text-xs text-muted-foreground">
                  A DPIA template ships with the product (docs/dpia-template.md) for
                  customers to complete per deployment, especially with API-based LLMs.
                </p>
              </div>
              <Badge variant="secondary">Template provided</Badge>
            </div>

            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Certifications</p>
                <p className="text-xs text-muted-foreground">
                  ISO 27001 readiness is on a dated, budgeted roadmap. Until then: audit
                  export, RLS tenant isolation, RBAC, and contractual audit rights.
                </p>
              </div>
              <Badge variant="warning">Roadmapped</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Governance Architecture</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>PolicyRule blocking before approval</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Compliance concern auto-blocks action</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Audit trail for all AI outputs — exportable above</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Evidence + confidence + limitations on every claim</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Scheduled outcome re-measurement — real data only</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Per-problem evidence packs for audits</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
