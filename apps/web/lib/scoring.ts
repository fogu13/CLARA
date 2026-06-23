import type { ImpactFactors } from "./types";

const weights: Record<keyof ImpactFactors, number> = {
  customer_reach: 1,
  severity: 1.25,
  recurrence: 1,
  journey_criticality: 1.2,
  account_exposure: 0.9,
  financial_exposure: 0.9,
  regulatory_risk: 1.1,
  evidence_confidence: 1
};

function clamp(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function impactScore(factors: ImpactFactors): number {
  const totalWeight = Object.values(weights).reduce((total, weight) => total + weight, 0);
  const weightedScore = Object.entries(weights).reduce((total, [factor, weight]) => {
    return total + clamp(factors[factor as keyof ImpactFactors]) * weight;
  }, 0);

  return Number((weightedScore / totalWeight).toFixed(3));
}

export function impactBand(score: number): string {
  if (score >= 0.78) return "critical";
  if (score >= 0.58) return "high";
  if (score >= 0.38) return "medium";
  return "low";
}

