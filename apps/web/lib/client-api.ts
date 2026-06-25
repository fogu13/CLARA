import type {
  ApprovalDecision,
  ApprovalRecord,
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
  ExecutionRecord,
  FeedbackRule,
  JiraIssueDraft,
  JourneyEventImportResult,
  JourneyEventRecord,
  LanguageQualityReport,
  LearningConclusionRecord,
  LearningConclusionRequest,
  OutcomeBoard,
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
  SystemConfig,
  TaxonomyCatalog,
  TaxonomyType,
  TerminologyDictionaryEntry,
  WorkflowState,
  WorkspaceSettings
} from "./types";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function trustedHeaders(): Record<string, string> {
  return {
    "x-tenant-id": process.env.NEXT_PUBLIC_CLARA_TENANT_ID ?? "demo_tenant",
    "x-actor-id": process.env.NEXT_PUBLIC_CLARA_ACTOR_ID ?? "demo_reviewer"
  };
}

function browserAccessToken(): string | null {
  if (typeof window === "undefined") return null;

  try {
    return window.localStorage.getItem("clara_access_token");
  } catch {
    return null;
  }
}

export function apiHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers({
    "Content-Type": "application/json",
    ...trustedHeaders()
  });

  new Headers(headers).forEach((value, key) => merged.set(key, value));

  const token = browserAccessToken();
  if (token && !merged.has("Authorization")) {
    merged.set("Authorization", `Bearer ${token}`);
  }

  return merged;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: apiHeaders(init?.headers)
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? `Request failed with status ${response.status}`);
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

export async function getTerminologyDictionary(): Promise<TerminologyDictionaryEntry[]> {
  return requestJson<TerminologyDictionaryEntry[]>(`${apiBaseUrl()}/terminology-dictionary`);
}

export async function getWorkspace(): Promise<WorkspaceSettings> {
  return requestJson<WorkspaceSettings>(`${apiBaseUrl()}/workspace`);
}

export async function updateWorkspace(settings: WorkspaceSettings): Promise<WorkspaceSettings> {
  return requestJson<WorkspaceSettings>(`${apiBaseUrl()}/workspace`, {
    method: "PUT",
    body: JSON.stringify(settings)
  });
}

export async function getSystemConfig(): Promise<SystemConfig> {
  return requestJson<SystemConfig>(`${apiBaseUrl()}/system-config`);
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
