import {
  fallbackEmergingProblems,
  fallbackPolicyRules,
  fallbackProblems,
  fallbackTaxonomies,
  fallbackTerminologyDictionary
} from "./sample-data";
import type {
  EmergingProblemReport,
  PolicyRule,
  ProblemRecord,
  ProblemSummary,
  TerminologyDictionaryEntry,
  TaxonomyCatalog
} from "./types";

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// Sample/demo data must be OPT-IN. Silently substituting it on any API error made a
// broken/unreachable backend look like real customer data. When the flag is off we log
// and re-throw so the failure is visible instead of faked.
const ALLOW_SAMPLE_DATA = process.env.NEXT_PUBLIC_ALLOW_SAMPLE_DATA === "true";

function onApiError<T>(context: string, error: unknown, sample: T): T {
  console.error(`[api] ${context} failed`, error);
  if (ALLOW_SAMPLE_DATA) return sample;
  throw error instanceof Error ? error : new Error(String(error));
}

export async function getActionQueueProblems(): Promise<ProblemRecord[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const summaries = await fetchJson<ProblemSummary[]>(`${apiUrl}/problems`);
    return Promise.all(
      summaries.map((problem) => fetchJson<ProblemRecord>(`${apiUrl}/problems/${problem.problem_id}`))
    );
  } catch (error) {
    return onApiError("getActionQueueProblems", error, fallbackProblems);
  }
}

export async function getPolicyRules(): Promise<PolicyRule[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<PolicyRule[]>(`${apiUrl}/policy-rules`);
  } catch (error) {
    return onApiError("getPolicyRules", error, fallbackPolicyRules);
  }
}

export async function getTaxonomies(): Promise<TaxonomyCatalog[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<TaxonomyCatalog[]>(`${apiUrl}/taxonomies`);
  } catch (error) {
    return onApiError("getTaxonomies", error, fallbackTaxonomies);
  }
}

export async function getTerminologyDictionary(): Promise<TerminologyDictionaryEntry[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<TerminologyDictionaryEntry[]>(`${apiUrl}/terminology-dictionary`);
  } catch (error) {
    return onApiError("getTerminologyDictionary", error, fallbackTerminologyDictionary);
  }
}

export async function getEmergingProblems(): Promise<EmergingProblemReport> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    return await fetchJson<EmergingProblemReport>(`${apiUrl}/emerging-problems`);
  } catch (error) {
    return onApiError("getEmergingProblems", error, fallbackEmergingProblems);
  }
}
