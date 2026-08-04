import type {
  ApprovalDecision,
  ApprovalRecord,
  Article50Status,
  ActionProposalUpdateRequest,
  ClosureRecord,
  ClosureRecordRequest,
  AffectedContextExplorer,
  CandidateReviewRequest,
  CustomerContextCompletenessReport,
  CustomerContextImportResult,
  CustomerContextRecord,
  CustomerContextValidationReport,
  DemoDatasetImportResult,
  DemoDatasetSummary,
  EmergingProblemReport,
  ExecutionRecord,
  FeedbackRule,
  JiraIssueDraft,
  JourneyEventImportResult,
  JourneyEventRecord,
  LanguageQualityReport,
  LearningConclusionRecord,
  LearningConclusionRequest,
  OutcomeBoard,
  OutcomeContractProposalPreview,
  OutcomeContractUpdateRequest,
  OutcomeMeasurement,
  OutcomeSnapshot,
  PolicyRule,
  ProblemCandidate,
  ProblemRecord,
  ProblemSummary,
  ProblemTransitionRecord,
  ProblemTransitionRequest,
  ProblemUpdateRequest,
  SignalImportResult,
  SignalRecord,
  SignalValidationReport,
  ModelCardMetrics,
  SystemConfig,
  TaxonomyBootstrapReport,
  TaxonomyCatalog,
  TaxonomyType,
  TerminologyDictionaryEntry,
  WorkflowState,
  WorkspaceSettings
} from "./types";
import { cookieAuthEnabled } from "./auth-client";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

// The canonical web origin the API's CORS accepts, derived from the API URL
// (api.clara.odradekai.com -> clara.odradekai.com). Used to steer users off a
// preview / non-canonical host, where every API call is browser-blocked by
// CORS and shows up as "API unreachable" + a failed token refresh.
export function canonicalWebUrl(): string | null {
  const api = process.env.NEXT_PUBLIC_API_URL;
  if (!api) return null;
  try {
    const url = new URL(api);
    return `${url.protocol}//${url.hostname.replace(/^api\./, "")}`;
  } catch {
    return null;
  }
}

// A one-line hint appended to connectivity errors when the browser is on an
// origin the API won't accept (notably *.vercel.app preview URLs). Empty when
// the origin already matches the canonical site, so it never nags in prod.
export function wrongOriginHint(): string {
  if (typeof window === "undefined") return "";
  const canonical = canonicalWebUrl();
  if (!canonical) return "";
  if (window.location.origin === canonical) return "";
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") return ""; // local dev
  return ` If you opened a preview or shared link, use the official app at ${canonical} instead.`;
}

function browserAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  // Cookie mode: the session is an HttpOnly cookie JS can't read. A token left
  // in localStorage by an older legacy-mode login would still go out as a Bearer
  // header, and the API prefers the header over the cookie (auth.py
  // get_current_user) — so a stale one 401s every request for a signed-in user.
  if (cookieAuthEnabled) return null;

  try {
    return window.localStorage.getItem("clara_access_token");
  } catch {
    return null;
  }
}

// Tenant and actor identity now come from the verified JWT server-side; the
// old x-tenant-id/x-actor-id headers are ignored by the API and no longer sent.
export function apiHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers({
    "Content-Type": "application/json"
  });

  new Headers(headers).forEach((value, key) => merged.set(key, value));

  const token = browserAccessToken();
  if (token && !merged.has("Authorization")) {
    merged.set("Authorization", `Bearer ${token}`);
  }

  return merged;
}

// Failures must stay visible (a 403 must never masquerade as an empty state),
// but a bare status code helps nobody — translate it once, here.
// For call sites that need the raw Response (file downloads, custom error
// handling): same transport rules as requestJson.
export function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  return fetch(url, {
    ...init,
    credentials: "include",
    headers: apiHeaders(init?.headers)
  });
}

export function httpErrorMessage(action: string, status: number): string {
  const reason =
    status === 401
      ? "your session is no longer valid — sign in again"
      : status === 403
        ? "you don't have permission (ask a workspace admin)"
        : status === 404
          ? "not found"
          : status >= 500
            ? "the server hit an error — try again shortly"
            : `request failed (HTTP ${status})`;
  return `${action}: ${reason}.`;
}

// All API traffic goes through here (or apiFetch below): credentials:"include"
// sends the HttpOnly session cookie to the same-site API in cookie-auth mode
// (fetch's default "same-origin" would drop it — same SITE, different ORIGIN).
// Harmless in legacy bearer mode, where no auth cookie exists.
async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    credentials: "include",
    headers: apiHeaders(init?.headers)
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? httpErrorMessage("Request failed", response.status));
  }

  return response.json() as Promise<T>;
}

export async function submitApproval(
  problemId: string,
  decision: ApprovalDecision
): Promise<ApprovalRecord> {
  return requestJson<ApprovalRecord>(`${apiBaseUrl()}/problems/${problemId}/approvals`, {
    method: "POST",
    body: JSON.stringify(decision)
  });
}

export async function getWorkflowState(problemId: string): Promise<WorkflowState> {
  return requestJson<WorkflowState>(`${apiBaseUrl()}/problems/${problemId}/workflow`);
}

export async function getProblems(): Promise<ProblemSummary[]> {
  return requestJson<ProblemSummary[]>(`${apiBaseUrl()}/problems`);
}

export async function getProblem(problemId: string): Promise<ProblemRecord> {
  return requestJson<ProblemRecord>(`${apiBaseUrl()}/problems/${problemId}`);
}

export async function getJiraDrafts(): Promise<JiraIssueDraft[]> {
  return requestJson<JiraIssueDraft[]>(`${apiBaseUrl()}/jira-drafts`);
}

export async function getApprovals(): Promise<ApprovalRecord[]> {
  return requestJson<ApprovalRecord[]>(`${apiBaseUrl()}/approvals`);
}

export async function getExecutions(): Promise<ExecutionRecord[]> {
  return requestJson<ExecutionRecord[]>(`${apiBaseUrl()}/executions`);
}

export async function updateProblem(
  problemId: string,
  update: ProblemUpdateRequest
): Promise<ProblemRecord> {
  return requestJson<ProblemRecord>(`${apiBaseUrl()}/problems/${problemId}`, {
    method: "PATCH",
    body: JSON.stringify(update)
  });
}

export async function updateActionProposal(
  problemId: string,
  actionId: string,
  update: ActionProposalUpdateRequest
): Promise<ProblemRecord> {
  return requestJson<ProblemRecord>(`${apiBaseUrl()}/problems/${problemId}/actions/${actionId}`, {
    method: "PATCH",
    body: JSON.stringify(update)
  });
}

export async function transitionProblem(
  problemId: string,
  transition: ProblemTransitionRequest
): Promise<ProblemTransitionRecord> {
  return requestJson<ProblemTransitionRecord>(`${apiBaseUrl()}/problems/${problemId}/transitions`, {
    method: "POST",
    body: JSON.stringify(transition)
  });
}

export async function recordClosure(
  problemId: string,
  closure: ClosureRecordRequest
): Promise<ClosureRecord> {
  return requestJson<ClosureRecord>(`${apiBaseUrl()}/problems/${problemId}/closure`, {
    method: "POST",
    body: JSON.stringify(closure)
  });
}

export async function getOutcomeSnapshot(problemId: string): Promise<OutcomeSnapshot> {
  return requestJson<OutcomeSnapshot>(`${apiBaseUrl()}/problems/${problemId}/outcome`);
}

export async function getContractProposal(
  problemId: string
): Promise<OutcomeContractProposalPreview> {
  return requestJson<OutcomeContractProposalPreview>(
    `${apiBaseUrl()}/problems/${problemId}/outcome-contract/proposal`
  );
}

export async function updateOutcomeContract(
  problemId: string,
  update: OutcomeContractUpdateRequest
): Promise<ProblemRecord> {
  return requestJson<ProblemRecord>(`${apiBaseUrl()}/problems/${problemId}/outcome-contract`, {
    method: "PATCH",
    body: JSON.stringify(update)
  });
}

export async function getOutcomeBoard(): Promise<OutcomeBoard> {
  return requestJson<OutcomeBoard>(`${apiBaseUrl()}/outcome-board`);
}

export async function recordOutcomeMeasurement(
  problemId: string,
  measurement: OutcomeMeasurement
): Promise<OutcomeMeasurement> {
  return requestJson<OutcomeMeasurement>(`${apiBaseUrl()}/problems/${problemId}/outcomes`, {
    method: "POST",
    body: JSON.stringify(measurement)
  });
}

export async function recordLearningConclusion(
  problemId: string,
  conclusion: LearningConclusionRequest
): Promise<LearningConclusionRecord> {
  return requestJson<LearningConclusionRecord>(`${apiBaseUrl()}/problems/${problemId}/learning-conclusions`, {
    method: "POST",
    body: JSON.stringify(conclusion)
  });
}

export async function getSignals(): Promise<SignalRecord[]> {
  return requestJson<SignalRecord[]>(`${apiBaseUrl()}/signals`);
}

export async function getEmergingProblems(): Promise<EmergingProblemReport> {
  return requestJson<EmergingProblemReport>(`${apiBaseUrl()}/emerging-problems`);
}

export type MeasurementPlan = {
  id: number;
  problem_id: string;
  execution_id: string;
  executed_at: string;
  due_at: string;
  kind: string;
  status: string;
  note?: string | null;
  created_at: string;
};

export type AskAnswer = {
  refused: boolean;
  reason?: string;
  answer: string | null;
  confidence: number;
  model_confidence?: number;
  retrieval_strength?: number;
  matches?: number;
  citations: {
    signal_id: string;
    source: string;
    language: string;
    timestamp: string;
    excerpt: string;
    similarity: number;
  }[];
};

export async function askClara(question: string): Promise<AskAnswer> {
  return requestJson<AskAnswer>(`${apiBaseUrl()}/ask`, {
    method: "POST",
    body: JSON.stringify({ question })
  });
}

export async function getMeasurements(): Promise<MeasurementPlan[]> {
  return requestJson<MeasurementPlan[]>(`${apiBaseUrl()}/measurements`);
}

export async function runDueMeasurements(): Promise<{ measured: number; manual_required: number; skipped: number }> {
  return requestJson(`${apiBaseUrl()}/measurements/run-due`, { method: "POST", body: JSON.stringify({}) });
}

export async function getJourneyEvents(): Promise<JourneyEventRecord[]> {
  return requestJson<JourneyEventRecord[]>(`${apiBaseUrl()}/journey-events`);
}

export async function importJourneyEvents(events: JourneyEventRecord[]): Promise<JourneyEventImportResult> {
  return requestJson<JourneyEventImportResult>(`${apiBaseUrl()}/journey-events/import`, {
    method: "POST",
    body: JSON.stringify({ events })
  });
}

export async function importJourneyEventCsv(csvText: string): Promise<JourneyEventImportResult> {
  return requestJson<JourneyEventImportResult>(`${apiBaseUrl()}/journey-events/import-csv`, {
    method: "POST",
    body: JSON.stringify({ csv_text: csvText })
  });
}

export async function getCustomerContext(): Promise<CustomerContextRecord[]> {
  return requestJson<CustomerContextRecord[]>(`${apiBaseUrl()}/customer-context`);
}

export async function getCustomerContextCompleteness(): Promise<CustomerContextCompletenessReport> {
  return requestJson<CustomerContextCompletenessReport>(
    `${apiBaseUrl()}/customer-context/completeness`
  );
}

export async function getAffectedContext(problemId: string): Promise<AffectedContextExplorer> {
  return requestJson<AffectedContextExplorer>(
    `${apiBaseUrl()}/problems/${problemId}/affected-context`
  );
}

export async function getPolicyRules(): Promise<PolicyRule[]> {
  return requestJson<PolicyRule[]>(`${apiBaseUrl()}/policy-rules`);
}

export async function getTaxonomies(): Promise<TaxonomyCatalog[]> {
  return requestJson<TaxonomyCatalog[]>(`${apiBaseUrl()}/taxonomies`);
}

export async function renameTaxonomyCategory(
  taxonomyType: TaxonomyType,
  body: { category_id: string; label: string; description?: string }
): Promise<TaxonomyCatalog> {
  return requestJson<TaxonomyCatalog>(
    `${apiBaseUrl()}/taxonomies/${taxonomyType}/categories/rename`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export async function lockTaxonomyCategory(
  taxonomyType: TaxonomyType,
  categoryId: string
): Promise<TaxonomyCatalog> {
  return requestJson<TaxonomyCatalog>(
    `${apiBaseUrl()}/taxonomies/${taxonomyType}/categories/lock`,
    { method: "POST", body: JSON.stringify({ category_id: categoryId }) }
  );
}

export async function bootstrapTaxonomy(
  body: { taxonomy_type?: TaxonomyType; limit?: number } = {}
): Promise<TaxonomyBootstrapReport> {
  return requestJson<TaxonomyBootstrapReport>(`${apiBaseUrl()}/taxonomy/bootstrap`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export type TaxonomyHygieneReport = {
  generated_at: string;
  duplicates: {
    taxonomy_type: string;
    category_a: string;
    label_a: string;
    category_b: string;
    label_b: string;
    similarity: number;
    suggestion: string;
  }[];
  duplicates_skipped: boolean;
  stale_proposals: { taxonomy_type: string; category_id: string; label: string; age_days: number; suggestion: string }[];
  drifted_categories: { taxonomy_type: string; category_id: string; label: string; window_days: number; suggestion: string }[];
  healthy: boolean;
};

export async function runTaxonomyHygiene(): Promise<TaxonomyHygieneReport> {
  return requestJson<TaxonomyHygieneReport>(`${apiBaseUrl()}/taxonomy/hygiene`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function reviewTaxonomyCategory(
  taxonomyType: TaxonomyType,
  body: { category_id: string; decision: "accept" | "reject" }
): Promise<TaxonomyCatalog> {
  return requestJson<TaxonomyCatalog>(
    `${apiBaseUrl()}/taxonomies/${taxonomyType}/categories/review`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export async function mergeTaxonomyCategories(
  taxonomyType: TaxonomyType,
  body: {
    source_category_ids: string[];
    target_category_id: string;
    target_label?: string;
    target_description?: string;
  }
): Promise<TaxonomyCatalog> {
  return requestJson<TaxonomyCatalog>(
    `${apiBaseUrl()}/taxonomies/${taxonomyType}/categories/merge`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export async function splitTaxonomyCategory(
  taxonomyType: TaxonomyType,
  body: {
    source_category_id: string;
    categories: { category_id: string; label: string; description: string }[];
  }
): Promise<TaxonomyCatalog> {
  return requestJson<TaxonomyCatalog>(
    `${apiBaseUrl()}/taxonomies/${taxonomyType}/categories/split`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export async function getTerminologyDictionary(): Promise<TerminologyDictionaryEntry[]> {
  return requestJson<TerminologyDictionaryEntry[]>(`${apiBaseUrl()}/terminology-dictionary`);
}

export async function getWorkspace(): Promise<WorkspaceSettings> {
  return requestJson<WorkspaceSettings>(`${apiBaseUrl()}/workspace`);
}

export async function updateWorkspace(
  settings: Partial<WorkspaceSettings>
): Promise<WorkspaceSettings> {
  // The API merges partial payloads: send only the fields you actually
  // changed, or a stale full object will overwrite concurrent writes.
  return requestJson<WorkspaceSettings>(`${apiBaseUrl()}/workspace`, {
    method: "PUT",
    body: JSON.stringify(settings)
  });
}

export async function getSystemConfig(): Promise<SystemConfig> {
  return requestJson<SystemConfig>(`${apiBaseUrl()}/system-config`);
}

export async function getModelCardMetrics(): Promise<ModelCardMetrics> {
  return requestJson<ModelCardMetrics>(`${apiBaseUrl()}/model-card/metrics`);
}

export async function getArticle50Status(): Promise<Article50Status> {
  return requestJson<Article50Status>(`${apiBaseUrl()}/article50-status`);
}

export async function getRules(): Promise<FeedbackRule[]> {
  return requestJson<FeedbackRule[]>(`${apiBaseUrl()}/rules`);
}

export async function createRule(rule: Omit<FeedbackRule, "rule_id">): Promise<FeedbackRule> {
  return requestJson<FeedbackRule>(`${apiBaseUrl()}/rules`, {
    method: "POST",
    body: JSON.stringify(rule)
  });
}

export async function deleteRule(ruleId: string): Promise<void> {
  await requestJson(`${apiBaseUrl()}/rules/${ruleId}`, { method: "DELETE" });
}

export async function getLanguageQuality(): Promise<LanguageQualityReport> {
  return requestJson<LanguageQualityReport>(`${apiBaseUrl()}/language-quality`);
}

export async function getDemoDatasets(): Promise<DemoDatasetSummary[]> {
  return requestJson<DemoDatasetSummary[]>(`${apiBaseUrl()}/demo-datasets`);
}

export async function importDemoDataset(datasetId: string): Promise<DemoDatasetImportResult> {
  return requestJson<DemoDatasetImportResult>(`${apiBaseUrl()}/demo-datasets/${datasetId}/import`, {
    method: "POST"
  });
}

export async function importCustomerContext(
  records: CustomerContextRecord[]
): Promise<CustomerContextImportResult> {
  return requestJson<CustomerContextImportResult>(`${apiBaseUrl()}/customer-context/import`, {
    method: "POST",
    body: JSON.stringify({ records })
  });
}

export async function importCustomerContextCsv(csvText: string): Promise<CustomerContextImportResult> {
  return requestJson<CustomerContextImportResult>(`${apiBaseUrl()}/customer-context/import-csv`, {
    method: "POST",
    body: JSON.stringify({ csv_text: csvText })
  });
}

export async function validateCustomerContextCsv(
  csvText: string
): Promise<CustomerContextValidationReport> {
  return requestJson<CustomerContextValidationReport>(`${apiBaseUrl()}/customer-context/validate-csv`, {
    method: "POST",
    body: JSON.stringify({ csv_text: csvText })
  });
}

export async function importSignals(signals: SignalRecord[]): Promise<SignalImportResult> {
  return requestJson<SignalImportResult>(`${apiBaseUrl()}/signals/import`, {
    method: "POST",
    body: JSON.stringify({ signals })
  });
}

export async function importSignalCsv(csvText: string): Promise<SignalImportResult> {
  return requestJson<SignalImportResult>(`${apiBaseUrl()}/signals/import-csv`, {
    method: "POST",
    body: JSON.stringify({ csv_text: csvText })
  });
}

export async function deleteSignals(signalIds: string[]): Promise<{ deleted: number }> {
  return requestJson<{ deleted: number }>(`${apiBaseUrl()}/signals/delete`, {
    method: "POST",
    body: JSON.stringify({ signal_ids: signalIds })
  });
}

export async function validateSignalCsv(csvText: string): Promise<SignalValidationReport> {
  return requestJson<SignalValidationReport>(`${apiBaseUrl()}/signals/validate-csv`, {
    method: "POST",
    body: JSON.stringify({ csv_text: csvText })
  });
}

export async function getProblemCandidates(): Promise<ProblemCandidate[]> {
  return requestJson<ProblemCandidate[]>(`${apiBaseUrl()}/problem-candidates`);
}

export async function promoteProblemCandidate(candidateId: string): Promise<ProblemRecord> {
  return requestJson<ProblemRecord>(`${apiBaseUrl()}/problem-candidates/${candidateId}/promote`, {
    method: "POST"
  });
}

export async function acceptProblemCandidate(
  candidateId: string,
  request: CandidateReviewRequest
): Promise<ProblemRecord> {
  return requestJson<ProblemRecord>(`${apiBaseUrl()}/problem-candidates/${candidateId}/accept`, {
    method: "POST",
    body: JSON.stringify(request)
  });
}

export async function rejectProblemCandidate(
  candidateId: string,
  request: CandidateReviewRequest
): Promise<ProblemCandidate> {
  return requestJson<ProblemCandidate>(`${apiBaseUrl()}/problem-candidates/${candidateId}/reject`, {
    method: "POST",
    body: JSON.stringify(request)
  });
}
