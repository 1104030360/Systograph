import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
      {
        id: "node:reference:output-guardrail",
        reference_node_id: "output_guardrail",
        plane_id: "governance_observability",
        type: "reference_capability",
        semantic_kind: "reference_capability",
        status: "undetermined",
        label: "Output Guardrail",
      },
    ],
    edges: [
      {
        id: "edge:query:loader-planner",
        from: "node:component:loader",
        to: "node:reference:planner",
        relationship: "provides context",
      },
      {
        id: "edge:control:planner-guardrail",
        from: "node:reference:planner",
        to: "node:reference:output-guardrail",
        relationship: "applies guardrail",
      },
    ],
    relationships: [
      {
        id: "relation:reference-component:planner:0",
        kind: "reference_component_mapping",
        source_node_id: "node:reference:planner",
        target_node_id: "node:component:loader",
        evidence_ids: [],
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
  it("renders the fixed ten-plane architecture and selects backend nodes", async () => {
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
    const flowToggle = screen.getByRole("button", { name: "Show backend-declared flows" });
    expect(flowToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Backend-declared flows")).toBeNull();
    fireEvent.click(flowToggle);
    expect(screen.getByText("Backend-declared flows")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Flow Document Loader to Planner" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide backend-declared flows" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(container.querySelectorAll("[data-plane-id]")).toHaveLength(10);
    expect(container.querySelector(".dr-edge-overlay")).toHaveAttribute("aria-hidden", "true");
    await waitFor(() => expect(container.querySelectorAll(".dr-edge-path.is-focused")).toHaveLength(3));
    expect(container.querySelectorAll(".dr-plane-connector")).toHaveLength(0);
    expect(screen.getByText("Input & Intent")).toBeInTheDocument();
    expect(screen.getByText("Deployment Topology")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Node Planner" }));
    expect(onSelect).toHaveBeenCalledWith({ kind: "node", id: "node:reference:planner" });
  });

  it("focuses only backend-matched connections for Data Flow", async () => {
    const graph = graphFixture();
    const { container } = render(
      <ArchitectureMap
        graph={graph}
        views={buildArchitectureViews(graph)}
        activeViewId="dataflow"
        search=""
        selected={null}
        onSelect={() => {}}
      />,
    );

    await waitFor(() =>
      expect(container.querySelector('[data-connection-id="edge:query:loader-planner"]')).toHaveClass("is-focused"),
    );
    expect(container.querySelector('[data-connection-id="relation:reference-component:planner:0"]')).toHaveClass(
      "is-focused",
    );
    expect(container.querySelector('[data-connection-id="edge:control:planner-guardrail"]')).toHaveClass("is-dimmed");
    expect(container.querySelector('[data-node-id="node:reference:output-guardrail"]')).toHaveClass("is-dimmed");
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

  it("applies transient trace classes without changing graph selection", async () => {
    const graph = graphFixture();
    const onSelect = vi.fn();
    const { container } = render(
      <ArchitectureMap
        graph={graph}
        views={buildArchitectureViews(graph)}
        activeViewId="overview"
        search=""
        selected={null}
        traceHighlight={{
          nodeIds: ["node:component:loader"],
          edgeIds: ["edge:query:loader-planner"],
          fallbackMessage: null,
        }}
        onSelect={onSelect}
      />,
    );

    expect(container.querySelector('[data-node-id="node:component:loader"]')).toHaveClass("is-trace-highlight");
    await waitFor(() =>
      expect(container.querySelector('[data-connection-id="edge:query:loader-planner"]')).toHaveClass(
        "is-trace-highlight",
      ),
    );
    expect(onSelect).not.toHaveBeenCalled();
  });
});
