import { describe, expect, it } from "vitest";
import { graphViewModelSchema } from "../types";
import { createFlowElements, layoutGraph, makeGraphIndexes } from "./graph";

const graph = graphViewModelSchema.parse({
  nodes: [
    { id: "node:a", label: "A" },
    { id: "node:b", label: "B" },
    { id: "node:c", label: "C" },
  ],
  edges: [
    { id: "edge:ab", from: "node:a", to: "node:b" },
    { id: "edge:bc", from: "node:b", to: "node:c" },
  ],
  details: {
    evidence_by_id: {},
    risk_hints_by_id: {},
    profile_findings_by_id: {},
    capability_candidates_by_id: {},
  },
  filters: {
    available: [],
    lenses: [
      {
        id: "lens:data",
        label: "Data",
        supported: true,
        matches_node_ids: ["node:a"],
        matches_edge_ids: ["edge:ab"],
      },
    ],
  },
});

describe("createFlowElements lens behavior", () => {
  it("highlights lens membership and dims the rest without removing anything", () => {
    const { nodes, edges } = createFlowElements(graph, {
      activeFilterIds: [],
      activeLensId: "lens:data",
    });

    expect(nodes).toHaveLength(3);
    expect(edges).toHaveLength(2);

    const byId = new Map(nodes.map((node) => [node.id, node.data]));
    expect(byId.get("node:a")).toMatchObject({ isFocused: true, isDimmed: false });
    expect(byId.get("node:b")).toMatchObject({ isFocused: false, isDimmed: true });
    expect(byId.get("node:c")).toMatchObject({ isFocused: false, isDimmed: true });

    const edgeById = new Map(edges.map((edge) => [edge.id, edge.data]));
    expect(edgeById.get("edge:ab")).toMatchObject({ isFocused: true, isDimmed: false });
    expect(edgeById.get("edge:bc")).toMatchObject({ isFocused: false, isDimmed: true });
  });

  it("does not dim anything when the active lens id is not published in this build", () => {
    const { nodes } = createFlowElements(graph, {
      activeFilterIds: [],
      activeLensId: "lens:stale",
    });

    nodes.forEach((node) => {
      expect(node.data.isDimmed).toBe(false);
    });
  });

  it("keeps lens and filter highlighting independent of each other", () => {
    const { nodes } = createFlowElements(graph, {
      activeFilterIds: [],
      activeLensId: null,
    });

    nodes.forEach((node) => {
      expect(node.data.isDimmed).toBe(false);
    });
  });
});

describe("makeGraphIndexes", () => {
  it("indexes the backend component identity published by the Plan 06 projection", () => {
    const projected = graphViewModelSchema.parse({
      nodes: [
        {
          id: "node:repo:agent",
          source_id: "canonical:agent",
          component_id: "component:agent",
          label: "Agent",
        },
      ],
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

    expect(makeGraphIndexes(projected).nodeIdBySource.get("component:agent")).toBe("node:repo:agent");
  });
});

describe("layoutGraph profile attachment overlay", () => {
  const overlayGraph = graphViewModelSchema.parse({
    nodes: [
      { id: "node:a", label: "A" },
      { id: "node:b", label: "B" },
      {
        id: "node:attach",
        label: "RAG grounding",
        semantic_kind: "profile_attachment",
        primary_anchor_node_id: "node:a",
        anchor_node_ids: ["node:a", "node:b"],
      },
      {
        id: "node:attach-2",
        label: "Reranking",
        semantic_kind: "profile_attachment",
        primary_anchor_node_id: "node:a",
        anchor_node_ids: ["node:a"],
      },
      {
        id: "node:attach-orphan",
        label: "Orphaned overlay",
        semantic_kind: "profile_attachment",
        anchor_node_ids: ["node:not-in-projection"],
      },
    ],
    edges: [{ id: "edge:ab", from: "node:a", to: "node:b" }],
    details: {
      evidence_by_id: {},
      risk_hints_by_id: {},
      profile_findings_by_id: {},
      capability_candidates_by_id: {},
    },
    filters: { available: [], lenses: [] },
  });

  it("stacks anchored attachments above their anchor instead of the layered layout", async () => {
    const elements = createFlowElements(overlayGraph, { activeFilterIds: [] });
    const layouted = await layoutGraph(elements.nodes, elements.edges);
    const byId = new Map(layouted.map((node) => [node.id, node.position]));

    const anchor = byId.get("node:a");
    const first = byId.get("node:attach");
    const second = byId.get("node:attach-2");
    if (!anchor || !first || !second) throw new Error("missing layout positions");

    expect(first.x).toBeGreaterThan(anchor.x);
    expect(first.y).toBeLessThan(anchor.y);
    expect(second.y).toBeLessThan(first.y);
  });

  it("keeps an attachment without a resolvable anchor visible in the main layout", async () => {
    const elements = createFlowElements(overlayGraph, { activeFilterIds: [] });
    const layouted = await layoutGraph(elements.nodes, elements.edges);
    const orphan = layouted.find((node) => node.id === "node:attach-orphan");

    expect(orphan).toBeDefined();
    // ELK assigns non-negative coordinates to layouted nodes; anchored overlays sit above (negative y).
    expect(orphan?.position.y).toBeGreaterThanOrEqual(0);
  });
});
