import type { AbLearning } from "@/lib/types";

const DAY_MS = 86_400_000;

/**
 * Confidence decay (design decision #2). A learning's stored confidence erodes
 * exponentially from `last_validated_at` with a configurable half-life.
 * Returns a 0–1 value.
 */
export function decayedConfidence(l: AbLearning, now: number = Date.now()): number {
  const base = l.evidence?.confidence ?? 0;
  const ref = l.last_validated_at ?? l.created_at;
  if (!ref) return base;
  const ageDays = Math.max(0, (now - new Date(ref).getTime()) / DAY_MS);
  const halfLife = l.half_life_days && l.half_life_days > 0 ? l.half_life_days : 180;
  return base * Math.pow(0.5, ageDays / halfLife);
}

/** A learning is "stale" once it has aged past its half-life (confidence below half its original). */
export function isStale(l: AbLearning, now: number = Date.now()): boolean {
  const base = l.evidence?.confidence ?? 0;
  return base > 0 && decayedConfidence(l, now) < base * 0.5;
}

const tokenize = (s: string) =>
  s.toLowerCase().split(/[^a-z0-9]+/).filter((t) => t.length > 2);

/**
 * "Relevant past learnings" retrieval (design decision #4): rank learnings by token
 * overlap with the query, weighted by decayed confidence so fresher/stronger learnings
 * surface first. (A pgvector semantic ranking can replace the scorer without changing callers.)
 */
export function rankLearnings(learnings: AbLearning[], query: string, k = 3): AbLearning[] {
  const qTokens = Array.from(new Set(tokenize(query)));
  if (qTokens.length === 0) return [];
  const now = Date.now();
  return learnings
    .map((l) => {
      const hay = `${l.topic} ${l.pattern} ${(l.evidence?.winning_examples ?? []).join(" ")} ${(l.evidence?.losing_examples ?? []).join(" ")}`.toLowerCase();
      const overlap = qTokens.reduce((n, t) => (hay.includes(t) ? n + 1 : n), 0);
      const score = overlap * (0.5 + 0.5 * decayedConfidence(l, now));
      return { l, score };
    })
    .filter((m) => m.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map((m) => m.l);
}
