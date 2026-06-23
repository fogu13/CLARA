import { describe, it, expect } from "vitest";
import { sampleSignals } from "./sample-data";

describe("sampleSignals", () => {
  it("returns workspace-scoped qualitative rows with tags + recorded_at", () => {
    const rows = sampleSignals(7);
    expect(rows.length).toBeGreaterThanOrEqual(5);
    for (const r of rows) {
      expect(r.workspace_id).toBe(7);
      expect(r.signal_type).toBe("qualitative");
      expect(typeof r.text_content).toBe("string");
      expect(Array.isArray(r.tags)).toBe(true);
      expect(typeof r.recorded_at).toBe("string");
    }
  });
});
