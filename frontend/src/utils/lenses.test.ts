import { describe, expect, it } from "vitest";
import type { GraphLensModel } from "../types";
import {
  GRAPH_STUDIO_LENS_KEYS,
  LENS_MEMBERSHIP_MISSING_REASON,
  canonicalLensKey,
  getLensMatches,
  resolveLensSlots,
} from "./lenses";

function lens(overrides: Partial<GraphLensModel> & { id: string; label: string }): GraphLensModel {
  return {
    supported: true,
    unavailable_reason: null,
    matches_node_ids: [],
    matches_edge_ids: [],
    ...overrides,
  };
}

describe("canonicalLensKey", () => {
  it("accepts the id spellings the backend may publish", () => {
    expect(canonicalLensKey("lens:data")).toBe("data");
    expect(canonicalLensKey("lens_data")).toBe("data");
    expect(canonicalLensKey("Data")).toBe("data");
    expect(canonicalLensKey(" governance ")).toBe("governance");
  });
});

describe("resolveLensSlots", () => {
  it("renders all six fixed lenses as missing when the payload has no membership", () => {
    const slots = resolveLensSlots([]);

    expect(slots.map((slot) => slot.key)).toEqual([...GRAPH_STUDIO_LENS_KEYS]);
    slots.forEach((slot) => {
      expect(slot.availability).toBe("missing");
      expect(slot.id).toBeNull();
      expect(slot.unavailableReason).toBe(LENS_MEMBERSHIP_MISSING_REASON);
    });
  });

  it("activates a fixed slot from backend membership and keeps the backend id", () => {
    const slots = resolveLensSlots([
      lens({ id: "lens:data", label: "Data", matches_node_ids: ["node:a", "node:b"], matches_edge_ids: ["edge:x"] }),
    ]);

    const dataSlot = slots.find((slot) => slot.key === "data");
    expect(dataSlot).toMatchObject({
      id: "lens:data",
      availability: "available",
      matchCount: 3,
      unavailableReason: null,
    });
    expect(slots.filter((slot) => slot.availability === "missing")).toHaveLength(5);
  });

  it("keeps an unsupported lens disabled with the backend-provided reason", () => {
    const slots = resolveLensSlots([
      lens({ id: "lens:risk", label: "Risk", supported: false, unavailable_reason: "risk sidecar not generated" }),
    ]);

    const riskSlot = slots.find((slot) => slot.key === "risk");
    expect(riskSlot).toMatchObject({
      availability: "unsupported",
      unavailableReason: "risk sidecar not generated",
    });
  });

  it("appends backend lenses outside the fixed six without dropping them", () => {
    const slots = resolveLensSlots([lens({ id: "lens:custom", label: "Custom view" })]);

    expect(slots).toHaveLength(GRAPH_STUDIO_LENS_KEYS.length + 1);
    expect(slots.at(-1)).toMatchObject({ id: "lens:custom", label: "Custom view", availability: "available" });
  });
});

describe("getLensMatches", () => {
  const published = [
    lens({ id: "lens:data", label: "Data", matches_node_ids: ["node:a"], matches_edge_ids: ["edge:x"] }),
    lens({ id: "lens:risk", label: "Risk", supported: false, matches_node_ids: ["node:b"] }),
  ];

  it("returns membership for an active supported lens", () => {
    const matches = getLensMatches(published, "lens:data");
    expect(matches.hasLens).toBe(true);
    expect([...matches.nodeIds]).toEqual(["node:a"]);
    expect([...matches.edgeIds]).toEqual(["edge:x"]);
  });

  it("ignores an active lens id that is unsupported or absent from this build", () => {
    expect(getLensMatches(published, "lens:risk").hasLens).toBe(false);
    expect(getLensMatches(published, "lens:stale-from-previous-build").hasLens).toBe(false);
    expect(getLensMatches(published, null).hasLens).toBe(false);
  });
});
