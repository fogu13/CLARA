"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, FileText, AlertTriangle, CheckCircle } from "lucide-react";

export default function CompliancePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Compliance</h1>
        <p className="text-sm text-muted-foreground mt-1">
          EU AI Act + GDPR assessment for customer feedback AI processing
        </p>
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
                  Human-in-the-loop approval for all consequential actions. The LangGraph
                  pipeline pauses at the approval interrupt before any external push.
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
                <p className="text-sm font-medium">Local-First Processing</p>
                <p className="text-xs text-muted-foreground">
                  Provider-agnostic AI layer supports Ollama/vLLM for on-premise processing.
                  No data leaves the EU when configured with local models.
                </p>
              </div>
              <Badge variant="success">Compliant</Badge>
            </div>

            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Risk Classification</p>
                <p className="text-xs text-muted-foreground">
                  Determine if the system qualifies as high-risk under Annex III.
                  Feedback triage is likely not Annex III, but document the assessment.
                </p>
              </div>
              <Badge variant="warning">Review Needed</Badge>
            </div>

            <div className="flex items-start gap-3">
              <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm font-medium">DPIA Documentation</p>
                <p className="text-xs text-muted-foreground">
                  A Data Protection Impact Assessment should be completed for the
                  feedback processing pipeline, especially when using API-based LLMs.
                </p>
              </div>
              <Badge variant="secondary">Pending</Badge>
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
              <span>Audit trail for all AI outputs</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Evidence + confidence + limitations on every claim</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
