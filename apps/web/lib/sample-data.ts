import sampleProblems from "../../../data/sample_problems.json";
import samplePolicyRules from "../../../data/sample_policy_rules.json";
import sampleTaxonomies from "../../../data/sample_taxonomies.json";
import sampleTerminologyDictionary from "../../../data/sample_terminology_dictionary.json";
import { impactBand, impactScore } from "./scoring";
import type {
  EmergingProblemReport,
  PolicyRule,
  ProblemRecord,
  TerminologyDictionaryEntry,
  TaxonomyCatalog
} from "./types";

export const fallbackProblems: ProblemRecord[] = (sampleProblems as unknown as ProblemRecord[]).map((problem) => {
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

export const fallbackPolicyRules: PolicyRule[] = samplePolicyRules as unknown as PolicyRule[];
export const fallbackTaxonomies: TaxonomyCatalog[] = sampleTaxonomies as unknown as TaxonomyCatalog[];
export const fallbackTerminologyDictionary: TerminologyDictionaryEntry[] =
  sampleTerminologyDictionary as unknown as TerminologyDictionaryEntry[];

export const fallbackEmergingProblems: EmergingProblemReport = {
  generated_at: new Date(0).toISOString(),
  candidate_count: 0,
  watch_count: 0,
  action_count: 0,
  signals: []
};

