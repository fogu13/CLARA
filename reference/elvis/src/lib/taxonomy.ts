import type { TaxonomyNode } from "./types";

export interface TaxonomyRow {
  category: string;
  theme: string;
  subtheme: string;
  description: string;
}

export function slugify(s: string): string {
  return s.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

/** Minimal CSV split honouring quoted fields (mirrors Signals.tsx parser). */
function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "", q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') { if (q && line[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
    else if (c === "," && !q) { out.push(cur); cur = ""; }
    else cur += c;
  }
  out.push(cur);
  return out.map((x) => x.trim());
}

export function parseTaxonomyFile(text: string, mime: string): TaxonomyRow[] {
  const norm = (r: Record<string, unknown>): TaxonomyRow => {
    const category = String(r.category ?? "").trim();
    if (!category) throw new Error("Every row needs a non-empty 'category'.");
    return {
      category,
      theme: String(r.theme ?? "").trim(),
      subtheme: String(r.subtheme ?? "").trim(),
      description: String(r.description ?? "").trim(),
    };
  };
  if (mime.includes("json") || text.trim().startsWith("[")) {
    const arr = JSON.parse(text);
    if (!Array.isArray(arr)) throw new Error("JSON taxonomy must be an array of rows.");
    return arr.map(norm);
  }
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) throw new Error("CSV needs a header row + at least one row.");
  const headers = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  return lines.slice(1).map((line) => {
    const cells = splitCsvLine(line);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => (row[h] = cells[i] ?? ""));
    return norm(row);
  });
}

/** Nest flat nodes into a tree by parent_id. */
export function buildTree(nodes: TaxonomyNode[]): TaxonomyNode[] {
  const byId = new Map(nodes.map((n) => [n.id, { ...n, children: [] as TaxonomyNode[] }]));
  const roots: TaxonomyNode[] = [];
  for (const n of byId.values()) {
    if (n.parent_id && byId.has(n.parent_id)) byId.get(n.parent_id)!.children!.push(n);
    else roots.push(n);
  }
  return roots;
}

export function coverage(mapped: number, total: number): number {
  return total > 0 ? mapped / total : 0;
}

export function cosineSim(a: number[], b: number[]): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom === 0 ? 0 : dot / denom;
}

/** Greedy single-pass clustering: each unused vector seeds a cluster of all unused vectors
 *  within `threshold` cosine. Returns clusters (as index arrays) with at least `minSize`. */
export function clusterByThreshold(vectors: number[][], threshold: number, minSize: number): number[][] {
  const used = new Array(vectors.length).fill(false);
  const clusters: number[][] = [];
  for (let i = 0; i < vectors.length; i++) {
    if (used[i]) continue;
    const group = [i];
    used[i] = true;
    for (let j = i + 1; j < vectors.length; j++) {
      if (!used[j] && cosineSim(vectors[i], vectors[j]) >= threshold) { group.push(j); used[j] = true; }
    }
    if (group.length >= minSize) clusters.push(group);
  }
  return clusters;
}

export interface CandidateEvidence {
  signal_ids: number[];
  samples: string[];
  size: number;
  cohesion: number;
}

export function candidateEvidence(signalIds: number[], texts: string[], cohesion: number): CandidateEvidence {
  return { signal_ids: signalIds, samples: texts.slice(0, 5), size: signalIds.length, cohesion };
}
