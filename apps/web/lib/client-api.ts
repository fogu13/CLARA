import type {
  ApprovalDecision,
  ApprovalRecord,
  ActionProposalUpdateRequest,
  AffectedContextExplorer,
  CandidateReviewRequest,
  CustomerContextCompletenessReport,
  CustomerContextImportResult,
  CustomerContextRecord,
  CustomerContextValidationReport,
  DemoDatasetImportResult,
  DemoDatasetSummary,
  ExecutionRecord,
  JiraIssueDraft,
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
  TaxonomyCatalog,
  TerminologyDictionaryEntry,
  WorkflowState
} from "./types";

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function trustedHeaders(): Record<string, string> {
  return {
    "x-tenant-id": process.env.NEXT_PUBLIC_CLARA_TENANT_ID ?? "demo_tenant",
    "x-actor-id": process.env.NEXT_PUBLIC_CLARA_ACTOR_ID ?? "demo_reviewer"
  };
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...trustedHeaders(),
      ...(init?.headers ?? {})
    }
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

export async function getTerminologyDictionary(): Promise<TerminologyDictionaryEntry[]> {
  return requestJson<TerminologyDictionaryEntry[]>(`${apiBaseUrl()}/terminology-dictionary`);
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
