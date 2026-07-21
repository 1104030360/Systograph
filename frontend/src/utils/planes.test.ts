import { describe, expect, it } from "vitest";
import { graphViewModelSchema } from "../types";
import { createFlowElements } from "./graph";
import { UNASSIGNED_PLANE_ID, hasBackendPlaneProjection, layoutPlaneBands } from "./planes";

function flowNodes(rawNodes: Array<Record<string, unknown>>) {
  const graph = graphViewModelSchema.parse({
    nodes: rawNodes,
    edges: [],
    details: {
      evidence_by_id: {},
      risk_hints_by_id: {},
      profile_findings_by_id: {},
      capability_candidates_by_id: {},
    },
    filters: { available: [], lenses: [] },
  });
  return createFlowElements(graph, { activeFilterIds: [] }).nodes;
}

describe("layoutPlaneBands", () => {
  it("recognizes a backend reference projection from the active v2 canonical source", () => {
    const graph = graphViewModelSchema.parse({
      source_schema_version: "ai-system-map/v2",
      reference_map_version: "1",
      nodes: [{ id: "reference:planner", label: "Planner", plane_id: "control" }],
      edges: [],
      details: {
        evidence_by_id: {},
        risk_hints_by_id: {},
        reference_assessments_by_id: {},
        profile_findings_by_id: {},
        capability_candidates_by_id: {},
      },
      filters: { available: [], lenses: [] },
    });

    expect(hasBackendPlaneProjection(graph)).toBe(true);
  });

  it("keeps a graph without backend plane metadata on auto layout", () => {
    const graph = graphViewModelSchema.parse({
      source_schema_version: "ai-system-map/v2",
      nodes: [{ id: "node:legacy", label: "Legacy" }],
      edges: [],
      details: {
        evidence_by_id: {},
        risk_hints_by_id: {},
        reference_assessments_by_id: {},
        profile_findings_by_id: {},
        capability_candidates_by_id: {},
      },
      filters: { available: [], lenses: [] },
    });

    expect(hasBackendPlaneProjection(graph)).toBe(false);
  });

  it("orders bands by the canonical plane order with unassigned last", () => {
    const { bands } = layoutPlaneBands(
      flowNodes([
        { id: "node:g", label: "Guardrail", plane_id: "governance_observability" },
        { id: "node:r", label: "Retriever", plane_id: "retrieval" },
        { id: "node:u", label: "Unplaced" },
        { id: "node:x", label: "Custom", plane_id: "custom_plane" },
      ]),
    );

    expect(bands.map((band) => band.id)).toEqual([
      "retrieval",
      "governance_observability",
      "custom_plane",
      UNASSIGNED_PLANE_ID,
    ]);
    expect(bands.at(-1)?.sublabel).toMatch(/not published/);
  });

  it("places every node inside its band rectangle with uniform band width", () => {
    const { positions, bands } = layoutPlaneBands(
      flowNodes([
        { id: "node:a", label: "A", plane_id: "retrieval" },
        { id: "node:b", label: "B", plane_id: "retrieval" },
        { id: "node:c", label: "C", plane_id: "generation" },
      ]),
    );

    const widths = new Set(bands.map((band) => band.width));
    expect(widths.size).toBe(1);

    bands.forEach((band) => {
      const ids = band.id === "retrieval" ? ["node:a", "node:b"] : ["node:c"];
      ids.forEach((id) => {
        const position = positions.get(id);
        if (!position) throw new Error(`missing position for ${id}`);
        expect(position.x).toBeGreaterThanOrEqual(band.x);
        expect(position.x).toBeLessThanOrEqual(band.x + band.width);
        expect(position.y).toBeGreaterThanOrEqual(band.y);
        expect(position.y).toBeLessThanOrEqual(band.y + band.height);
      });
    });
  });

  it("keeps anchored profile attachments stacked above their anchor inside the band", () => {
    const { positions, bands } = layoutPlaneBands(
      flowNodes([
        { id: "node:r", label: "Retriever", plane_id: "retrieval" },
        {
          id: "node:attach",
          label: "RAG grounding",
          semantic_kind: "profile_attachment",
          primary_anchor_node_id: "node:r",
          anchor_node_ids: ["node:r"],
        },
      ]),
    );

    const anchor = positions.get("node:r");
    const attachment = positions.get("node:attach");
    const band = bands.find((item) => item.id === "retrieval");
    if (!anchor || !attachment || !band) throw new Error("missing layout output");

    expect(attachment.y).toBeLessThan(anchor.y);
    expect(attachment.y).toBeGreaterThanOrEqual(band.y);
    expect(bands.map((item) => item.id)).toEqual(["retrieval"]);
  });

  it("degrades a payload without any plane_id into a single unassigned band", () => {
    const { bands } = layoutPlaneBands(
      flowNodes([
        { id: "node:a", label: "A" },
        { id: "node:b", label: "B" },
      ]),
    );

    expect(bands).toHaveLength(1);
    expect(bands[0].id).toBe(UNASSIGNED_PLANE_ID);
    expect(bands[0].count).toBe(2);
  });
});
