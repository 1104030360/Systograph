import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { graphViewModelSchema, type GraphViewModel } from "../types";
import { buildArchitectureViews } from "../utils/architectureViews";
import { ArchitectureMap } from "./ArchitectureMap";

function graphFixture(referenceMapVersion: string | null = "1"): GraphViewModel {
  return graphViewModelSchema.parse({
    schema_version: "ai-system-graph/v2",
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
        description: "Plans a sequence of work.",
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
          id: "lens:risk",
          label: "Risk",
          supported: true,
          matches_node_ids: ["node:component:loader"],
          matches_edge_ids: [],
        },
      ],
    },
  });
}

describe("ArchitectureMap", () => {
  it("renders the fixed ten-plane architecture and selects backend nodes", () => {
    const graph = graphFixture();
    const onSelect = vi.fn();
    const { container } = render(
      <ArchitectureMap
        graph={graph}
        views={buildArchitectureViews(graph)}
        activeViewId="overview"
        search=""
        selected={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByLabelText("AI Agent System, ten architecture planes")).toBeInTheDocument();
    expect(container.querySelectorAll("[data-plane-id]")).toHaveLength(10);
    expect(container.querySelectorAll(".dr-plane-connector[aria-hidden='true']")).toHaveLength(10);
    expect(screen.getByText("Input & Intent")).toBeInTheDocument();
    expect(screen.getByText("Deployment Topology")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Node Planner" }));
    expect(onSelect).toHaveBeenCalledWith({ kind: "node", id: "node:reference:planner" });
  });

  it("dims nodes outside the selected backend view without removing the ten-plane context", () => {
    const graph = graphFixture();
    const { container } = render(
      <ArchitectureMap
        graph={graph}
        views={buildArchitectureViews(graph)}
        activeViewId="risk"
        search=""
        selected={null}
        onSelect={() => {}}
      />,
    );

    expect(container.querySelector('[data-node-id="node:reference:planner"]')).toHaveClass("is-dimmed");
    expect(container.querySelector('[data-node-id="node:component:loader"]')).not.toHaveClass("is-dimmed");
    expect(container.querySelectorAll("[data-plane-id]")).toHaveLength(10);
  });

  it("does not fall back to the legacy whiteboard when plane metadata is absent", () => {
    const graph = graphFixture(null);
    render(
      <ArchitectureMap
        graph={graph}
        views={buildArchitectureViews(graph)}
        activeViewId="overview"
        search=""
        selected={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("note")).toHaveTextContent("No 10-plane projection");
    expect(screen.queryByLabelText("AI Agent System, ten architecture planes")).not.toBeInTheDocument();
  });
});
