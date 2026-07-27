import { describe, expect, it } from "vitest";
import { graphViewModelSchema, type GraphViewModel } from "../types";
import { ARCHITECTURE_VIEW_DEFINITIONS, buildArchitectureViews } from "./architectureViews";

function graphFixture(referenceMapVersion: string | null = "1"): GraphViewModel {
  return graphViewModelSchema.parse({
    schema_version: "ai-system-graph/v2",
    source_schema_version: "ai-system-map/v2",
    reference_map_version: referenceMapVersion,
    nodes: [
      {
        id: "node:reference:planner",
        reference_node_id: "planner",
        plane_id: "control",
        type: "reference_capability",
        semantic_kind: "reference_capability",
        status: "undetermined",
        label: "Planner",
        related_unmapped_component_ids: ["unmapped:router"],
      },
      {
        id: "node:component:loader",
        component_id: "component:loader",
        plane_id: "ingestion_indexing",
        type: "document_loader",
        semantic_kind: "repo_component",
        status: "detected",
        activation: "enabled",
        label: "Document Loader",
      },
      {
        id: "node:unmapped:router",
        source_id: "unmapped:router",
        type: "custom_router",
        semantic_kind: "unmapped_component",
        status: "needs_confirmation",
        label: "Custom Router",
      },
    ],
    edges: [
      {
        id: "edge:query:loader-planner",
        from: "node:component:loader",
        to: "node:reference:planner",
        relationship: "provides context",
      },
    ],
    details: {},
    filters: {
      lenses: [
        {
          id: "lens:data",
          label: "Data",
          supported: true,
          matches_node_ids: ["node:component:loader"],
          matches_edge_ids: ["edge:query:loader-planner"],
        },
        {
          id: "lens:control",
          label: "Control",
          supported: true,
          matches_node_ids: ["node:reference:planner"],
          matches_edge_ids: [],
        },
      ],
    },
  });
}

describe("buildArchitectureViews", () => {
  it("builds the fixed sixteen-view navigation from explicit backend metadata", () => {
    const views = buildArchitectureViews(graphFixture());

    expect(views.map((view) => view.id)).toEqual(ARCHITECTURE_VIEW_DEFINITIONS.map((view) => view.id));
    expect(views).toHaveLength(16);
    expect(new Set(views.find((view) => view.id === "dataflow")?.matchesNodeIds)).toEqual(
      new Set(["node:component:loader", "node:reference:planner"]),
    );
    expect(views.find((view) => view.id === "ingestion")?.matchesNodeIds).toEqual(["node:component:loader"]);
    expect(views.find((view) => view.id === "known")?.matchesNodeIds).toEqual(["node:reference:planner"]);
    expect(new Set(views.find((view) => view.id === "unmapped")?.matchesNodeIds)).toEqual(
      new Set(["node:reference:planner", "node:unmapped:router"]),
    );
  });

  it("keeps contract gaps disabled instead of inferring their membership", () => {
    const views = buildArchitectureViews(graphFixture());

    for (const id of ["runtime", "variants", "reasoning", "source", "risk"] as const) {
      expect(views.find((view) => view.id === id)?.supported).toBe(false);
      expect(views.find((view) => view.id === id)?.unavailableReason).toBeTruthy();
    }
  });

  it("requires reference-map metadata before enabling plane-derived views", () => {
    const views = buildArchitectureViews(graphFixture(null));

    expect(views.find((view) => view.id === "overview")?.supported).toBe(true);
    expect(views.find((view) => view.id === "ingestion")?.supported).toBe(false);
    expect(views.find((view) => view.id === "known")?.supported).toBe(false);
  });
});
