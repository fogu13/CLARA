import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/contexts/AuthContext";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  ShieldCheck, ShieldAlert, ShieldX, Upload, FileText,
  Trash2, Loader2, CheckCircle2, XCircle, AlertTriangle,
  ChevronDown, ChevronUp, History, Plus, Minus, Scale,
  AlertCircle, Clock
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

// ─── Types ──────────────────────────────────────────────────────────────────

interface Finding {
  regulation: string;
  area: string;
  article: string;
  status: "pass" | "fail" | "warning" | "not_applicable";
  score: number;
  finding: string;
  recommendation?: string;
}

interface RequiredAction {
  priority: "critical" | "high" | "medium" | "low";
  action: string;
  regulation: string;
  deadline: string;
}

interface ComplianceResult {
  overall_score: number;
  risk_level: "critical" | "high" | "medium" | "low" | "minimal";
  summary: string;
  gdpr_score: number;
  eu_ai_act_score: number;
  findings: Finding[];
  required_actions: RequiredAction[];
  compliant_aspects: string[];
  prohibited_practices_detected: string[];
}

interface ComplianceDoc {
  id: string;
  name: string;
  description: string | null;
  file_path: string;
  file_size: number | null;
  content_extracted: string | null;
  created_at: string;
}

interface ComplianceCheck {
  id: string;
  title: string;
  campaign_description: string;
  overall_score: number;
  gdpr_score: number;
  eu_ai_act_score: number;
  risk_level: string;
  summary: string | null;
  findings: Finding[];
  required_actions: RequiredAction[];
  compliant_aspects: string[];
  status: string;
  created_at: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getRiskColor(risk: string) {
  switch (risk) {
    case "critical": return "text-destructive";
    case "high": return "text-orange-500";
    case "medium": return "text-yellow-500";
    case "low": return "text-blue-500";
    case "minimal": return "text-primary";
    default: return "text-muted-foreground";
  }
}

function getRiskBg(risk: string) {
  switch (risk) {
    case "critical": return "bg-destructive/10 border-destructive/20 text-destructive";
    case "high": return "bg-orange-500/10 border-orange-500/20 text-orange-500";
    case "medium": return "bg-yellow-500/10 border-yellow-500/20 text-yellow-500";
    case "low": return "bg-blue-500/10 border-blue-500/20 text-blue-500";
    case "minimal": return "bg-primary/10 border-primary/20 text-primary";
    default: return "bg-muted";
  }
}

function getScoreColor(score: number) {
  if (score >= 90) return "text-primary";
  if (score >= 70) return "text-blue-500";
  if (score >= 50) return "text-yellow-500";
  if (score >= 30) return "text-orange-500";
  return "text-destructive";
}

function getProgressColor(score: number) {
  if (score >= 90) return "bg-primary";
  if (score >= 70) return "bg-blue-500";
  if (score >= 50) return "bg-yellow-500";
  if (score >= 30) return "bg-orange-500";
  return "bg-destructive";
}

function StatusIcon({ status }: { status: Finding["status"] }) {
  switch (status) {
    case "pass": return <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />;
    case "fail": return <XCircle className="h-4 w-4 text-destructive shrink-0" />;
    case "warning": return <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0" />;
    default: return <Minus className="h-4 w-4 text-muted-foreground shrink-0" />;
  }
}

function PriorityBadge({ priority }: { priority: RequiredAction["priority"] }) {
  const map = {
    critical: "bg-destructive/10 text-destructive border-destructive/20",
    high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    low: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  };
  return (
    <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded border uppercase tracking-wide", map[priority])}>
      {priority}
    </span>
  );
}

// ─── Score Gauge ─────────────────────────────────────────────────────────────

function ScoreGauge({ score, label, size = "md" }: { score: number; label: string; size?: "sm" | "md" | "lg" }) {
  const r = size === "lg" ? 52 : size === "md" ? 38 : 28;
  const stroke = size === "lg" ? 8 : size === "md" ? 6 : 5;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const dim = (r + stroke) * 2;
  const textSize = size === "lg" ? "text-3xl" : size === "md" ? "text-xl" : "text-base";

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative flex items-center justify-center" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} className="-rotate-90">
          <circle cx={r + stroke} cy={r + stroke} r={r} stroke="hsl(var(--border))" strokeWidth={stroke} fill="none" />
          <circle
            cx={r + stroke} cy={r + stroke} r={r}
            stroke={score >= 70 ? "hsl(var(--primary))" : score >= 50 ? "#eab308" : score >= 30 ? "#f97316" : "hsl(var(--destructive))"}
            strokeWidth={stroke} fill="none"
            strokeDasharray={circ} strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.8s ease" }}
          />
        </svg>
        <span className={cn("absolute font-bold tabular-nums", textSize, getScoreColor(score))}>{score}</span>
      </div>
      <span className="text-xs text-muted-foreground font-medium">{label}</span>
    </div>
  );
}

// ─── Finding Card ─────────────────────────────────────────────────────────────

function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn(
      "rounded-lg border p-3 transition-colors",
      finding.status === "pass" ? "border-primary/20 bg-primary/5" :
      finding.status === "fail" ? "border-destructive/20 bg-destructive/5" :
      finding.status === "warning" ? "border-yellow-500/20 bg-yellow-500/5" :
      "border-border bg-muted/30"
    )}>
      <button className="w-full flex items-start gap-2.5 text-left" onClick={() => setOpen(o => !o)}>
        <StatusIcon status={finding.status} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-foreground">{finding.area}</span>
            <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{finding.article}</span>
            <span className={cn(
              "text-[10px] font-bold px-1.5 py-0.5 rounded",
              finding.regulation === "GDPR" ? "bg-blue-500/10 text-blue-500" : "bg-purple-500/10 text-purple-500"
            )}>{finding.regulation}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{finding.finding}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={cn("text-sm font-bold tabular-nums", getScoreColor(finding.score))}>{finding.score}</span>
          {open ? <ChevronUp className="h-3 w-3 text-muted-foreground" /> : <ChevronDown className="h-3 w-3 text-muted-foreground" />}
        </div>
      </button>
      {open && (
        <div className="mt-2.5 pl-6 space-y-1.5">
          <p className="text-xs text-foreground/80">{finding.finding}</p>
          {finding.recommendation && (
            <div className="flex gap-1.5 text-xs text-muted-foreground bg-muted/50 rounded p-2">
              <AlertCircle className="h-3 w-3 shrink-0 mt-0.5 text-primary" />
              <span>{finding.recommendation}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const workspaceId = useWorkspaceId();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [result, setResult] = useState<ComplianceResult | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [docName, setDocName] = useState("");
  const [docDescription, setDocDescription] = useState("");
  const [activeTab, setActiveTab] = useState("checker");

  // Fetch compliance documents
  const { data: docs = [], refetch: refetchDocs } = useQuery<ComplianceDoc[]>({
    queryKey: ["compliance-docs", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("compliance_documents")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data as ComplianceDoc[];
    },
    enabled: !!workspaceId,
  });

  // Fetch compliance history
  const { data: history = [] } = useQuery<ComplianceCheck[]>({
    queryKey: ["compliance-checks", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("compliance_checks")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("created_at", { ascending: false })
        .limit(20);
      if (error) throw error;
      return data as unknown as ComplianceCheck[];
    },
    enabled: !!workspaceId,
  });

  // Delete doc mutation
  const deleteDocMutation = useMutation({
    mutationFn: async (doc: ComplianceDoc) => {
      const { error: storageError } = await supabase.storage.from("compliance-docs").remove([doc.file_path]);
      if (storageError) throw storageError;
      const { error } = await supabase.from("compliance_documents").delete().eq("id", doc.id).eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      refetchDocs();
      toast.success("Document removed");
    },
    onError: (err: Error) => {
      toast.error("Failed to delete document", { description: err.message });
    },
  });

  // Upload doc handler
  const handleDocUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !workspaceId) return;
    if (!docName.trim()) {
      toast.error("Please enter a document name");
      return;
    }
    setUploadingDoc(true);
    try {
      const filePath = `${workspaceId}/${Date.now()}-${file.name}`;
      const { error: uploadError } = await supabase.storage
        .from("compliance-docs")
        .upload(filePath, file);
      if (uploadError) throw uploadError;

      // For text files, extract content
      let contentExtracted: string | null = null;
      if (file.type === "text/plain") {
        contentExtracted = await file.text();
        if (contentExtracted.length > 50000) contentExtracted = contentExtracted.substring(0, 50000);
      }

      const { error: dbError } = await supabase.from("compliance_documents").insert({
        workspace_id: workspaceId,
        name: docName.trim(),
        description: docDescription.trim() || null,
        file_path: filePath,
        file_size: file.size,
        content_extracted: contentExtracted,
      });
      if (dbError) throw dbError;

      toast.success("Document uploaded successfully");
      setDocName("");
      setDocDescription("");
      refetchDocs();
      e.target.value = "";
    } catch (err: unknown) {
      toast.error("Upload failed", { description: (err as Error).message });
    } finally {
      setUploadingDoc(false);
    }
  }, [workspaceId, docName, docDescription, refetchDocs]);

  // Run compliance check
  const handleCheck = async () => {
    if (!title.trim() || !description.trim()) {
      toast.error("Please fill in a title and description");
      return;
    }
    if (!workspaceId) {
      toast.error("No workspace found");
      return;
    }
    setIsChecking(true);
    setResult(null);

    try {
      // Gather selected doc content
      const additionalDocuments = docs
        .filter(d => selectedDocs.includes(d.id) && d.content_extracted)
        .map(d => ({ name: d.name, content: d.content_extracted! }));

      const { data: fnData, error: fnError } = await supabase.functions.invoke("check-compliance", {
        body: {
          title: title.trim(),
          campaignDescription: description.trim(),
          additionalDocuments,
        },
      });

      if (fnError) throw fnError;
      if (fnData?.error) throw new Error(fnData.error);

      const assessment = fnData as ComplianceResult;
      setResult(assessment);

      // Save to DB
      const { error: saveError } = await supabase.from("compliance_checks").insert({
        workspace_id: workspaceId,
        title: title.trim(),
        campaign_description: description.trim(),
        overall_score: assessment.overall_score,
        gdpr_score: assessment.gdpr_score,
        eu_ai_act_score: assessment.eu_ai_act_score,
        risk_level: assessment.risk_level,
        summary: assessment.summary,
        findings: assessment.findings as unknown as never,
        required_actions: assessment.required_actions as unknown as never,
        compliant_aspects: assessment.compliant_aspects as unknown as never,
        document_ids: selectedDocs,
        status: "completed",
      });
      if (saveError) {
        toast.error("Check completed but failed to save to history", { description: saveError.message });
      }

      queryClient.invalidateQueries({ queryKey: ["compliance-checks", workspaceId] });
    } catch (err: unknown) {
      const msg = (err as Error).message;
      if (msg.includes("429") || msg.includes("Rate limit")) {
        toast.error("Rate limit reached", { description: "Please wait a moment and try again." });
      } else if (msg.includes("402") || msg.includes("credits")) {
        toast.error("Credits required", { description: "Please add usage credits to your workspace." });
      } else {
        toast.error("Check failed", { description: msg });
      }
    } finally {
      setIsChecking(false);
    }
  };

  const gdprFindings = result?.findings.filter(f => f.regulation === "GDPR") ?? [];
  const aiActFindings = result?.findings.filter(f => f.regulation === "EU AI Act") ?? [];

  return (
    <AppLayout title="EU Compliance">
      <div className="max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Scale className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">EU Compliance Checker</h1>
              <p className="text-sm text-muted-foreground">
                Assess marketing campaigns against GDPR and EU AI Act requirements with AI-powered analysis
              </p>
            </div>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="checker">Check Campaign</TabsTrigger>
              <TabsTrigger value="documents">
                Local Documents
                {docs.length > 0 && (
                  <span className="ml-1.5 text-[10px] bg-primary/15 text-primary px-1.5 py-0.5 rounded-full font-medium">
                    {docs.length}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            {/* ── Checker Tab ── */}
            <TabsContent value="checker" className="space-y-5 mt-5">
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
                {/* Input Panel */}
                <div className="lg:col-span-2 space-y-4">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">Campaign Details</CardTitle>
                      <CardDescription className="text-xs">Describe your marketing use case or campaign in detail for the most accurate assessment.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="space-y-1.5">
                        <Label className="text-xs">Campaign Title</Label>
                        <Input
                          placeholder="e.g. AI-powered email re-engagement"
                          value={title}
                          onChange={e => setTitle(e.target.value)}
                          className="text-sm h-9"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Campaign Description</Label>
                        <Textarea
                          placeholder="Describe your campaign: what data you collect, how you use AI, who you target, what channels, what personalisation techniques, how consent is managed..."
                          value={description}
                          onChange={e => setDescription(e.target.value)}
                          className="text-sm min-h-[180px] resize-none"
                        />
                      </div>

                      {docs.length > 0 && (
                        <div className="space-y-1.5">
                          <Label className="text-xs">Include Local Documents</Label>
                          <div className="space-y-1.5">
                            {docs.filter(d => d.content_extracted).map(doc => (
                              <label key={doc.id} className="flex items-center gap-2 text-xs cursor-pointer rounded-md border p-2 hover:bg-muted/50 transition-colors">
                                <input
                                  type="checkbox"
                                  checked={selectedDocs.includes(doc.id)}
                                  onChange={e => setSelectedDocs(prev =>
                                    e.target.checked ? [...prev, doc.id] : prev.filter(id => id !== doc.id)
                                  )}
                                  className="accent-primary"
                                />
                                <FileText className="h-3 w-3 text-muted-foreground shrink-0" />
                                <span className="text-foreground font-medium truncate">{doc.name}</span>
                              </label>
                            ))}
                            {docs.filter(d => !d.content_extracted).length > 0 && (
                              <p className="text-[10px] text-muted-foreground">
                                Note: Only .txt documents can be included in analysis. PDF content extraction coming soon.
                              </p>
                            )}
                          </div>
                        </div>
                      )}

                      <Button
                        className="w-full"
                        onClick={handleCheck}
                        disabled={isChecking || !title.trim() || !description.trim()}
                      >
                        {isChecking ? (
                          <><Loader2 className="h-4 w-4 animate-spin" /> Analysing…</>
                        ) : (
                          <><ShieldCheck className="h-4 w-4" /> Run Compliance Check</>
                        )}
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Regulation Reference */}
                  <Card className="bg-muted/30">
                    <CardContent className="p-3 space-y-2">
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Regulations Checked</p>
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                          <span className="text-xs text-foreground font-medium">GDPR (EU) 2016/679</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                          <span className="text-xs text-foreground font-medium">EU AI Act 2024/1689 (incl. 2026 Omnibus)</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                          <span className="text-xs text-muted-foreground">ePrivacy / PECR</span>
                        </div>
                        {selectedDocs.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                            <span className="text-xs text-muted-foreground">+{selectedDocs.length} local document(s)</span>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Results Panel */}
                <div className="lg:col-span-3 space-y-4">
                  {!result && !isChecking && (
                    <div className="flex flex-col items-center justify-center h-64 rounded-lg border border-dashed border-border text-center gap-3">
                      <ShieldCheck className="h-10 w-10 text-muted-foreground/40" />
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">No assessment yet</p>
                        <p className="text-xs text-muted-foreground/70">Fill in the campaign details and run a check</p>
                      </div>
                    </div>
                  )}

                  {isChecking && (
                    <div className="flex flex-col items-center justify-center h-64 rounded-lg border border-border gap-3">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      <div className="text-center">
                        <p className="text-sm font-medium text-foreground">Analysing compliance…</p>
                        <p className="text-xs text-muted-foreground">Checking against GDPR & EU AI Act requirements</p>
                      </div>
                    </div>
                  )}

                  {result && (
                    <div className="space-y-4">
                      {/* Score Overview */}
                      <Card>
                        <CardContent className="pt-5 pb-4">
                          <div className="flex flex-col sm:flex-row items-center gap-6">
                            <ScoreGauge score={result.overall_score} label="Overall Score" size="lg" />
                            <div className="flex gap-6">
                              <ScoreGauge score={result.gdpr_score} label="GDPR" size="md" />
                              <ScoreGauge score={result.eu_ai_act_score} label="EU AI Act" size="md" />
                            </div>
                            <div className="flex-1 space-y-2">
                              <div className={cn("inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border", getRiskBg(result.risk_level))}>
                                {result.risk_level === "critical" || result.risk_level === "high" ? (
                                  <ShieldX className="h-3.5 w-3.5" />
                                ) : result.risk_level === "medium" ? (
                                  <ShieldAlert className="h-3.5 w-3.5" />
                                ) : (
                                  <ShieldCheck className="h-3.5 w-3.5" />
                                )}
                                {result.risk_level.charAt(0).toUpperCase() + result.risk_level.slice(1)} Risk
                              </div>
                              <p className="text-xs text-muted-foreground leading-relaxed">{result.summary}</p>
                            </div>
                          </div>

                          {result.prohibited_practices_detected.length > 0 && (
                            <div className="mt-4 rounded-lg bg-destructive/10 border border-destructive/20 p-3 space-y-1.5">
                              <p className="text-xs font-semibold text-destructive flex items-center gap-1.5">
                                <XCircle className="h-3.5 w-3.5" /> Prohibited Practices Detected
                              </p>
                              {result.prohibited_practices_detected.map((p, i) => (
                                <p key={i} className="text-xs text-destructive/80 pl-5">{p}</p>
                              ))}
                            </div>
                          )}
                        </CardContent>
                      </Card>

                      {/* Required Actions */}
                      {result.required_actions.length > 0 && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Required Actions</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-2">
                            {result.required_actions.map((action, i) => (
                              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-muted/40 border border-border">
                                <PriorityBadge priority={action.priority} />
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs text-foreground">{action.action}</p>
                                  <div className="flex items-center gap-3 mt-1">
                                    <span className={cn(
                                      "text-[10px] font-medium px-1.5 py-0.5 rounded",
                                      action.regulation === "GDPR" ? "bg-blue-500/10 text-blue-500" : "bg-purple-500/10 text-purple-500"
                                    )}>{action.regulation}</span>
                                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                                      <Clock className="h-2.5 w-2.5" />{action.deadline}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </CardContent>
                        </Card>
                      )}

                      {/* Findings by Regulation */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {gdprFindings.length > 0 && (
                          <Card>
                            <CardHeader className="pb-2">
                              <div className="flex items-center gap-2">
                                <div className="h-2 w-2 rounded-full bg-blue-500" />
                                <CardTitle className="text-sm">GDPR Findings</CardTitle>
                                <span className={cn("ml-auto text-sm font-bold tabular-nums", getScoreColor(result.gdpr_score))}>{result.gdpr_score}/100</span>
                              </div>
                            </CardHeader>
                            <CardContent className="space-y-2">
                              {gdprFindings.map((f, i) => <FindingCard key={i} finding={f} />)}
                            </CardContent>
                          </Card>
                        )}
                        {aiActFindings.length > 0 && (
                          <Card>
                            <CardHeader className="pb-2">
                              <div className="flex items-center gap-2">
                                <div className="h-2 w-2 rounded-full bg-purple-500" />
                                <CardTitle className="text-sm">EU AI Act Findings</CardTitle>
                                <span className={cn("ml-auto text-sm font-bold tabular-nums", getScoreColor(result.eu_ai_act_score))}>{result.eu_ai_act_score}/100</span>
                              </div>
                            </CardHeader>
                            <CardContent className="space-y-2">
                              {aiActFindings.map((f, i) => <FindingCard key={i} finding={f} />)}
                            </CardContent>
                          </Card>
                        )}
                      </div>

                      {/* Compliant Aspects */}
                      {result.compliant_aspects.length > 0 && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <CheckCircle2 className="h-4 w-4 text-primary" /> Compliant Aspects
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="flex flex-wrap gap-2">
                              {result.compliant_aspects.map((a, i) => (
                                <span key={i} className="text-xs bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-full">
                                  {a}
                                </span>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* ── Documents Tab ── */}
            <TabsContent value="documents" className="space-y-5 mt-5">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Upload Local Compliance Documents</CardTitle>
                  <CardDescription className="text-xs">
                    Add your own regulatory guidelines, internal policies, or local legislation amendments. Text (.txt) documents will be included in analysis; PDFs are stored for reference.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Document Name *</Label>
                      <Input
                        placeholder="e.g. German BDSG Amendment"
                        value={docName}
                        onChange={e => setDocName(e.target.value)}
                        className="text-sm h-9"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Description (optional)</Label>
                      <Input
                        placeholder="Brief description"
                        value={docDescription}
                        onChange={e => setDocDescription(e.target.value)}
                        className="text-sm h-9"
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">File</Label>
                    <label className={cn(
                      "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border p-6 cursor-pointer transition-colors",
                      uploadingDoc ? "opacity-50 pointer-events-none" : "hover:border-primary/50 hover:bg-muted/30"
                    )}>
                      {uploadingDoc ? (
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      ) : (
                        <Upload className="h-6 w-6 text-muted-foreground" />
                      )}
                      <span className="text-sm text-muted-foreground">
                        {uploadingDoc ? "Uploading…" : "Click to upload PDF or TXT"}
                      </span>
                      <span className="text-[10px] text-muted-foreground/60">Max 10MB · PDF, TXT, DOCX</span>
                      <input type="file" className="hidden" accept=".pdf,.txt,.doc,.docx" onChange={handleDocUpload} disabled={uploadingDoc} />
                    </label>
                  </div>
                </CardContent>
              </Card>

              {docs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 rounded-lg border border-dashed border-border gap-2">
                  <FileText className="h-8 w-8 text-muted-foreground/40" />
                  <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {docs.map(doc => (
                    <Card key={doc.id}>
                      <CardContent className="p-3 flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{doc.name}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            {doc.description && <p className="text-xs text-muted-foreground truncate">{doc.description}</p>}
                            {doc.file_size && (
                              <span className="text-[10px] text-muted-foreground shrink-0">
                                {(doc.file_size / 1024).toFixed(0)}KB
                              </span>
                            )}
                            <span className={cn(
                              "text-[10px] px-1.5 py-0.5 rounded shrink-0",
                              doc.content_extracted ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                            )}>
                              {doc.content_extracted ? "✓ Indexed" : "Stored only"}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[10px] text-muted-foreground">{format(new Date(doc.created_at), "MMM d")}</span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            onClick={() => deleteDocMutation.mutate(doc)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* ── History Tab ── */}
            <TabsContent value="history" className="space-y-4 mt-5">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 rounded-lg border border-dashed border-border gap-2">
                  <History className="h-8 w-8 text-muted-foreground/40" />
                  <p className="text-sm text-muted-foreground">No checks run yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map(check => (
                    <Card
                      key={check.id}
                      className="cursor-pointer hover:border-primary/30 transition-colors"
                      onClick={() => {
                        setTitle(check.title);
                        setDescription(check.campaign_description);
                        setResult({
                          overall_score: check.overall_score,
                          gdpr_score: check.gdpr_score,
                          eu_ai_act_score: check.eu_ai_act_score,
                          risk_level: check.risk_level as ComplianceResult["risk_level"],
                          summary: check.summary ?? "",
                          findings: check.findings,
                          required_actions: check.required_actions,
                          compliant_aspects: check.compliant_aspects,
                          prohibited_practices_detected: [],
                        });
                        setActiveTab("checker");
                      }}
                    >
                      <CardContent className="p-3 flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-foreground truncate">{check.title}</p>
                            <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full border shrink-0", getRiskBg(check.risk_level))}>
                              {check.risk_level}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{check.summary}</p>
                          <p className="text-[10px] text-muted-foreground mt-1">{format(new Date(check.created_at), "MMM d, yyyy · HH:mm")}</p>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <div className="text-center">
                            <p className={cn("text-lg font-bold tabular-nums", getScoreColor(check.overall_score))}>{check.overall_score}</p>
                            <p className="text-[10px] text-muted-foreground">Score</p>
                          </div>
                          <div className="flex gap-2">
                            <div className="text-center">
                              <p className={cn("text-xs font-bold tabular-nums", getScoreColor(check.gdpr_score))}>{check.gdpr_score}</p>
                              <p className="text-[9px] text-muted-foreground">GDPR</p>
                            </div>
                            <div className="text-center">
                              <p className={cn("text-xs font-bold tabular-nums", getScoreColor(check.eu_ai_act_score))}>{check.eu_ai_act_score}</p>
                              <p className="text-[9px] text-muted-foreground">AI Act</p>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
    </AppLayout>
  );
}
