import { describe, expect, it } from "vitest";
import { graphViewModelSchema } from "../types";
import { createFlowElements } from "./graph";

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
