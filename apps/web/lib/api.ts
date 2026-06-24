import sampleProblems from "../../../data/sample_problems.json";
import samplePolicyRules from "../../../data/sample_policy_rules.json";
import sampleTaxonomies from "../../../data/sample_taxonomies.json";
import sampleTerminologyDictionary from "../../../data/sample_terminology_dictionary.json";
import { impactBand, impactScore } from "./scoring";
import type {
  EmergingProblemReport,
  PolicyRule,
  ProblemRecord,
  ProblemSummary,
  TerminologyDictionaryEntry,
  TaxonomyCatalog
} from "./types";

const fallbackProblems = (sampleProblems as unknown as ProblemRecord[]).map((problem) => {
  const score = impactScore(problem.impact_factors);
  const governanceFailures = problem.governance_checks.filter(
    (check) => check.blocking && check.status === "fail"
  ).length;

  return {
    ...problem,
    impact_score: score,
    impact_band: impactBand(score),
    approval_pressure:
      problem.status === "blocked_by_policy" || governanceFailures > 0
        ? "blocked"
        : problem.status === "approval_needed"
          ? "needs_review"
          : "ready"
  };
});

const fallbackPolicyRules = samplePolicyRules as unknown as PolicyRule[];
const fallbackTaxonomies = sampleTaxonomies as unknown as TaxonomyCatalog[];
const fallbackTerminologyDictionary =
  sampleTerminologyDictionary as unknown as TerminologyDictionaryEntry[];
const fallbackEmergingProblems: EmergingProblemReport = {
  generated_at: new Date(0).toISOString(),
  candidate_count: 0,
  watch_count: 0,
  action_count: 0,
  signals: []
};

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getActionQueueProblems(): Promise<ProblemRecord[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const summaries = await fetchJson<ProblemSummary[]>(`${apiUrl}/problems`);
    return Promise.all(
      summaries.map((problem) => fetchJson<ProblemRecord>(`${apiUrl}/problems/${problem.problem_id}`))
    );
  } catch {
    return fallbackProblems;
  }
}

export async function getPolicyRules(): Promise<PolicyRule[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<PolicyRule[]>(`${apiUrl}/policy-rules`);
  } catch {
    return fallbackPolicyRules;
  }
}

export async function getTaxonomies(): Promise<TaxonomyCatalog[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<TaxonomyCatalog[]>(`${apiUrl}/taxonomies`);
  } catch {
    return fallbackTaxonomies;
  }
}

export async function getTerminologyDictionary(): Promise<TerminologyDictionaryEntry[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<TerminologyDictionaryEntry[]>(`${apiUrl}/terminology-dictionary`);
  } catch {
    return fallbackTerminologyDictionary;
  }
}

export async function getEmergingProblems(): Promise<EmergingProblemReport> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<EmergingProblemReport>(`${apiUrl}/emerging-problems`);
  } catch {
    return fallbackEmergingProblems;
  }
}
