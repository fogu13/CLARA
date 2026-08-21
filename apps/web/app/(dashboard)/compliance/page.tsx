"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, FileText, AlertTriangle, BookOpen, CheckCircle, Download, Cpu, Globe, HelpCircle, UserX, Server, Scale } from "lucide-react";
import { apiBaseUrl, apiHeaders, getArticle50Status, getModelCardMetrics, getSystemConfig, getWorkspace } from "@/lib/client-api";
import type { Article50Status, ModelCardMetrics, SystemConfig, WorkspaceSettings } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

export default function CompliancePage() {
  const { t } = useI18n();
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [art50, setArt50] = useState<Article50Status | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceSettings | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [evalMetrics, setEvalMetrics] = useState<ModelCardMetrics | null>(null);

  useEffect(() => {
    getSystemConfig().then(setConfig).catch(() => {});
    getArticle50Status().then(setArt50).catch(() => {});
    getWorkspace().then(setWorkspace).catch(() => {});
    getModelCardMetrics().then(setEvalMetrics).catch(() => {});
  }, []);

  async function downloadCsv(entity: string) {
    try {
      const res = await fetch(`${apiBaseUrl()}/export/${entity}.csv`, { credentials: "include", headers: apiHeaders() });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const url = URL.createObjectURL(await res.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${entity}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Export failed");
    }
  }

  async function downloadAuditLog() {
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/audit-export`, { credentials: "include", headers: apiHeaders() });
      if (!res.ok) {
        // Only blame the role when it IS the role; a down API is not a 403.
        throw new Error(
          res.status === 403
            ? `Export failed (403). Admin role required.`
            : `Export failed (${res.status})`
        );
      }
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

  function downloadArticle50Status() {
    setExportError(null);
    if (!art50) {
      setExportError(t.compliance.art50Unavailable);
      return;
    }
    const blob = new Blob([JSON.stringify(art50, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `clara-article50-status-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const aiHost = (() => {
    try {
      return config ? new URL(config.ai_base_url).host : null;
    } catch {
      return config?.ai_base_url ?? null;
    }
  })();

  const art50Compliant =
    art50 !== null && art50.auto_published.disclosed_count >= art50.auto_published.count;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t.compliance.title}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t.compliance.subtitle}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button onClick={() => void downloadAuditLog()} disabled={exporting}>
            <Download className="mr-1 h-4 w-4" />
            {exporting ? t.compliance.exporting : t.compliance.downloadAudit}
          </Button>
          {exportError ? <p className="text-xs text-destructive">{exportError}</p> : null}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm text-muted-foreground">{t.compliance.overallScore}</CardTitle>
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">87</div>
            <p className="text-xs text-muted-foreground mt-1">{t.compliance.outOf}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">GDPR</CardTitle></CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">92</div>
            <p className="text-xs text-muted-foreground mt-1">Lawful basis + data minimization · self-assessed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">EU AI Act</CardTitle></CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">82</div>
            <p className="text-xs text-muted-foreground mt-1">Transparency + human oversight · self-assessed</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Cpu className="h-4 w-4" /> {t.compliance.modelCard}</CardTitle>
            <CardDescription>{t.compliance.modelCardSubtitle}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {config ? (
              <>
                <div className="flex justify-between"><span className="text-muted-foreground">{t.compliance.model}</span><code className="bg-muted px-2 py-0.5 rounded">{config.ai_model}</code></div>
                <div className="flex justify-between"><span className="text-muted-foreground">{t.compliance.endpoint}</span><code className="bg-muted px-2 py-0.5 rounded">{aiHost}</code></div>
                <div className="flex justify-between"><span className="text-muted-foreground">{t.compliance.apiAuth}</span><Badge variant={config.auth_enabled ? "success" : "warning"}>{config.auth_enabled ? t.compliance.enabled : t.compliance.disabledDev}</Badge></div>
              </>
            ) : (
              <p className="text-muted-foreground">{t.compliance.configUnavailable}</p>
            )}
            {evalMetrics?.published && evalMetrics.overall ? (
              <div className="mt-3 rounded-md border p-2 text-xs">
                <p className="font-semibold">
                  Measured quality — n={evalMetrics.dataset?.total_items}, {evalMetrics.published_at?.slice(0, 10)}, {evalMetrics.model}
                </p>
                <div className="mt-1 grid grid-cols-3 gap-2">
                  <span>Sentiment {Math.round(evalMetrics.overall.sentiment_accuracy * 100)}% (CI {Math.round(evalMetrics.overall.sentiment_ci95[0] * 100)}–{Math.round(evalMetrics.overall.sentiment_ci95[1] * 100)}%)</span>
                  <span>Urgency {Math.round(evalMetrics.overall.urgency_accuracy * 100)}% (CI {Math.round(evalMetrics.overall.urgency_ci95[0] * 100)}–{Math.round(evalMetrics.overall.urgency_ci95[1] * 100)}%)</span>
                  <span>Tag F1 (fuzzy) {Math.round(evalMetrics.overall.tag_f1_fuzzy * 100)}%</span>
                </div>
                {evalMetrics.by_language ? (
                  <div className="mt-1 space-y-0.5 text-muted-foreground">
                    {Object.entries(evalMetrics.by_language).map(([lang, m]) => (
                      <p key={lang}>
                        {lang.toUpperCase()} (n={m.n}): sentiment {m.sentiment_accuracy != null ? `${Math.round(m.sentiment_accuracy * 100)}%` : "–"} · urgency {m.urgency_accuracy != null ? `${Math.round(m.urgency_accuracy * 100)}%` : "–"}
                      </p>
                    ))}
                  </div>
                ) : null}
                <p className="mt-1 text-muted-foreground">{evalMetrics.dataset?.note}</p>
              </div>
            ) : (
              <p className="mt-3 text-xs text-muted-foreground">
                No published evaluation snapshot yet — run the eval harness with --publish.
              </p>
            )}
            <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
              <li>• Purpose: classify + summarize customer feedback; propose (never execute) actions.</li>
              <li>• Provider-agnostic (OpenAI-compatible): routable to EU-hosted or fully local models (Ollama/vLLM).</li>
              <li>• No fine-tuning on customer data. Adaptation happens via retrieval, taxonomy and outcome learnings.</li>
              <li>• Every AI output carries confidence, evidence links and stated limitations.</li>
              <li>• Known limitations: non-deterministic outputs; quality tracked by a published eval harness.</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Scale className="h-4 w-4" /> {t.compliance.art50Title}</CardTitle>
            <CardDescription>{t.compliance.art50Subtitle}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {art50 ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t.compliance.art50HumanReviewed}</span>
                  <span className="font-medium">{art50.human_reviewed.count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t.compliance.art50AutoPublished}</span>
                  <span className="font-medium">
                    {art50.auto_published.count}
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({art50.auto_published.disclosed_count} {t.compliance.art50Disclosed})
                    </span>
                  </span>
                </div>
                {art50.by_destination.length > 0 ? (
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="py-1 font-medium">{t.compliance.art50Destination}</th>
                        <th className="py-1 font-medium">{t.compliance.art50HumanReviewed}</th>
                        <th className="py-1 font-medium">{t.compliance.art50Disclosed}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {art50.by_destination.map((row) => (
                        <tr key={row.destination} className="border-t">
                          <td className="py-1">{row.destination}</td>
                          <td className="py-1">{row.human_reviewed}</td>
                          <td className="py-1">{row.disclosed}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-xs text-muted-foreground">{t.compliance.art50NoExecutions}</p>
                )}
                <Button size="sm" variant="outline" onClick={downloadArticle50Status}>
                  <Download className="mr-1 h-3 w-3" /> {t.compliance.art50Export}
                </Button>
              </>
            ) : (
              <p className="text-muted-foreground">{t.compliance.art50Unavailable}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><BookOpen className="h-4 w-4" /> {t.aiLiteracy.compTitle}</CardTitle>
            <CardDescription>{t.aiLiteracy.compSubtitle}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">{t.aiLiteracy.packAttestation}</span>
              {workspace?.ai_literacy_pack_delivered_at ? (
                <Badge variant="success">
                  {t.aiLiteracy.attestedOn.replace("{date}", workspace.ai_literacy_pack_delivered_at)}
                </Badge>
              ) : (
                <Badge variant="secondary">{t.aiLiteracy.notAttested}</Badge>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/ai-literacy"
                className="inline-flex items-center rounded-md border px-3 py-1 text-xs font-medium hover:bg-muted"
              >
                {t.aiLiteracy.compOpen}
              </Link>
              <Link
                href="/ai-literacy/pack"
                className="inline-flex items-center rounded-md border px-3 py-1 text-xs font-medium hover:bg-muted"
              >
                <Download className="mr-1 h-3 w-3" aria-hidden="true" /> {t.aiLiteracy.compPack}
              </Link>
            </div>
            <p className="text-xs text-muted-foreground">{t.aiLiteracy.attestNote}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Globe className="h-4 w-4" /> {t.compliance.residency}</CardTitle>
            <CardDescription>{t.compliance.residencySubtitle}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.residency1}</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.residency2}</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.residency3}</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.residency4}</span></div>
            <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.residency5}</span></div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><UserX className="h-4 w-4" /> {t.compliance.rights}</CardTitle>
          <CardDescription>{t.compliance.rightsSubtitle}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="rounded-md border p-3">
            <p className="font-medium">{t.complianceProse.exportTitle}</p>
            <code className="mt-1 block text-xs bg-muted rounded px-2 py-1">GET /customers/&#123;customer_id&#125;/data-export</code>
            <p className="mt-1 text-xs text-muted-foreground">{t.complianceProse.exportDesc}</p>
          </div>
          <div className="rounded-md border p-3">
            <p className="font-medium">{t.complianceProse.erasureTitle}</p>
            <code className="mt-1 block text-xs bg-muted rounded px-2 py-1">DELETE /customers/&#123;customer_id&#125;/data</code>
            <p className="mt-1 text-xs text-muted-foreground">
              {t.complianceProse.erasureDesc}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Server className="h-4 w-4" /> {t.compliance.subprocessors}</CardTitle>
          <CardDescription>{t.compliance.subprocessorsSubtitle}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.subprocessors1}</span></div>
          <div className="flex items-start gap-2"><CheckCircle className="mt-0.5 h-4 w-4 text-emerald-500" /><span>{t.complianceProse.subprocessors2}</span></div>
          <div className="rounded-md border p-3">
            <p className="font-medium">{t.compliance.securityContact}</p>
            {workspace?.notification_email ? (
              <code className="mt-1 block text-xs bg-muted rounded px-2 py-1">{workspace.notification_email}</code>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">{t.complianceProse.securityContactNone}</p>
            )}
            <p className="mt-1 text-xs text-muted-foreground">{t.complianceProse.incidentNotice}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.compliance.assessment}</CardTitle>
          <CardDescription>{t.compliance.assessmentSubtitle}</CardDescription>
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
              {art50 === null ? (
                <HelpCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
              ) : art50Compliant ? (
                <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
              )}
              <div>
                <p className="text-sm font-medium">{t.complianceProse.transparencyTitle}</p>
                <p className="text-xs text-muted-foreground">
                  {t.complianceProse.transparencyDesc}
                  {art50 ? (
                    <>
                      {" "}
                      {art50.human_reviewed.count} {t.compliance.art50HumanReviewed} ·{" "}
                      {art50.auto_published.count} {t.compliance.art50AutoPublished}.
                    </>
                  ) : null}
                </p>
              </div>
              {art50 ? (
                <Badge variant={art50Compliant ? "success" : "warning"}>
                  {art50Compliant ? t.compliance.art50BadgeOk : t.compliance.art50BadgeGap}
                </Badge>
              ) : (
                <Badge variant="secondary">{t.compliance.art50BadgeUnknown}</Badge>
              )}
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
                  minimal/limited risk, not an Annex III use case. See docs/eu-ai-act-mapping.md.
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
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Download className="h-4 w-4" /> {t.compliance.exportsBi}</CardTitle>
          <CardDescription>{t.compliance.exportsBiSubtitle}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 text-sm">
          {["signals", "problems", "outcomes", "telemetry"].map((entity) => (
            <button
              key={entity}
              type="button"
              onClick={() => downloadCsv(entity)}
              className="inline-flex items-center rounded-md border px-3 py-1 text-xs font-medium hover:bg-muted"
            >
              <Download className="mr-1 h-3 w-3" /> {entity}.csv
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t.compliance.governanceArchitecture}</CardTitle></CardHeader>
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
              <span>Audit trail for all AI outputs, exportable above</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Evidence + confidence + limitations on every claim</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Scheduled outcome re-measurement, real data only</span>
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
