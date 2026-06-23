import { describe, it, expect } from "vitest";
import { slugify, parseTaxonomyFile, buildTree, coverage } from "./taxonomy";
import { cosineSim, clusterByThreshold, candidateEvidence } from "./taxonomy";
import type { TaxonomyNode } from "./types";

describe("slugify", () => {
  it("lowercases, trims, and underscores", () => {
    expect(slugify("  Checkout Failure! ")).toBe("checkout_failure");
  });
});

describe("parseTaxonomyFile", () => {
  it("parses CSV into category/theme/subtheme rows", () => {
    const csv = "category,theme,subtheme,description\nBilling,Checkout,payment_declined,Card declined\n";
    const rows = parseTaxonomyFile(csv, "text/csv");
    expect(rows).toEqual([
      { category: "Billing", theme: "Checkout", subtheme: "payment_declined", description: "Card declined" },
    ]);
  });

  it("parses JSON array form", () => {
    const json = JSON.stringify([{ category: "Billing", theme: "Checkout", subtheme: "payment_declined" }]);
    const rows = parseTaxonomyFile(json, "application/json");
    expect(rows[0].category).toBe("Billing");
    expect(rows[0].description ?? "").toBe("");
  });

  it("throws when a row has no category", () => {
    expect(() => parseTaxonomyFile("category,theme\n,Checkout\n", "text/csv")).toThrow();
  });
});

describe("buildTree", () => {
  it("nests level 2 and 3 under their parents", () => {
    const flat = [
      { id: "c", parent_id: null, level: 1, name: "Billing" },
      { id: "t", parent_id: "c", level: 2, name: "Checkout" },
      { id: "s", parent_id: "t", level: 3, name: "declined" },
    ] as TaxonomyNode[];
    const tree = buildTree(flat);
    expect(tree).toHaveLength(1);
    expect(tree[0].children?.[0].children?.[0].name).toBe("declined");
  });
});

describe("coverage", () => {
  it("is mapped / total, 0 when no signals", () => {
    expect(coverage(8, 10)).toBeCloseTo(0.8);
    expect(coverage(0, 0)).toBe(0);
  });
});

describe("cosineSim", () => {
  it("is 1 for identical, 0 for orthogonal", () => {
    expect(cosineSim([1, 0], [1, 0])).toBeCloseTo(1);
    expect(cosineSim([1, 0], [0, 1])).toBeCloseTo(0);
  });
});

describe("clusterByThreshold", () => {
  it("groups vectors above the threshold, drops singletons below minSize", () => {
    const vecs = [[1, 0], [0.99, 0.01], [0, 1]];
    const clusters = clusterByThreshold(vecs, 0.9, 2);
    expect(clusters).toEqual([[0, 1]]);
  });
});

describe("candidateEvidence", () => {
  it("summarises ids + first samples + size", () => {
    const ev = candidateEvidence([3, 4, 5], ["a", "b", "c", "d", "e", "f"], 0.81);
    expect(ev.size).toBe(3);
    expect(ev.signal_ids).toEqual([3, 4, 5]);
    expect(ev.samples.length).toBeLessThanOrEqual(5);
    expect(ev.cohesion).toBeCloseTo(0.81);
  });
});
