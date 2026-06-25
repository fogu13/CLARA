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
