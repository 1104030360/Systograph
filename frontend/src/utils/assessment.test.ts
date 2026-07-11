import { describe, expect, it } from "vitest";
import { nodeStatusKey, nodeStatusLabel } from "./assessment";

describe("assessment presentation", () => {
  it("preserves backend-owned Phase 2 status even when risk hints exist", () => {
    expect(nodeStatusKey({ status: "partial", risk_hint_ids: ["risk:exposure"] })).toBe("partial");
    expect(nodeStatusKey({ status: "conflicted", risk_hint_ids: ["risk:exposure"] })).toBe("conflicted");
  });

  it("keeps legacy risk precedence for legacy node states", () => {
    expect(nodeStatusKey({ status: "missing", risk_hint_ids: ["risk:exposure"] })).toBe("risk");
  });

  it("uses readable labels without inventing new assessment semantics", () => {
    expect(nodeStatusLabel("not_detected")).toBe("not detected");
    expect(nodeStatusLabel("needs_review")).toBe("needs review");
  });
});
