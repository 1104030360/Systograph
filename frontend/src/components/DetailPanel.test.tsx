import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { graphViewModelSchema, viewerPayloadSchema } from "../types";
import { DetailPanel } from "./DetailPanel";

const graph = graphViewModelSchema.parse({
  nodes: [
    { id: "node:coordinator", label: "Coordinator", plane_id: "control" },
    { id: "node:legacy", label: "Legacy component" },
    { id: "node:frontier", label: "Frontier component", plane_id: "trust_boundary" },
  ],
  edges: [],
  details: {
    evidence_by_id: {},
    risk_hints_by_id: {},
    profile_findings_by_id: {},
    capability_candidates_by_id: {},
  },
  filters: { available: [], lenses: [] },
});

const payload = viewerPayloadSchema.parse({
  contract_source: "phase2-build",
  viewer_load_result: {
    loaded: true,
    project_id: null,
    scan_id: null,
    build_id: null,
    environment_id: null,
    generated_from_build_id: null,
    ai_system_map: {},
    profile_inference_result: null,
    readiness_report: null,
    graph_view_model: graph,
  },
});

function renderPanel(nodeId: string) {
  return render(
    <DetailPanel
      graph={graph}
      payload={payload}
      selected={{ kind: "node", id: nodeId }}
      detailMode="overview"
      onDetailModeChange={() => {}}
      onClose={() => {}}
    />,
  );
}

describe("DetailPanel plane chip", () => {
  it("shows an icon plus text label when the backend published plane_id", () => {
    const { container } = renderPanel("node:coordinator");

    const chip = container.querySelector(".plane-chip");
    expect(chip).not.toBeNull();
    expect(chip).toHaveTextContent("Control");
    const icon = chip?.querySelector("svg");
    expect(icon).not.toBeNull();
    expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  it("renders no plane chip at all when plane_id is missing", () => {
    const { container } = renderPanel("node:legacy");

    expect(container.querySelector(".plane-chip")).toBeNull();
  });

  it("shows the text label but no icon for a plane outside the registry", () => {
    const { container } = renderPanel("node:frontier");

    const chip = container.querySelector(".plane-chip");
    expect(chip).not.toBeNull();
    expect(chip).toHaveTextContent("Trust Boundary");
    expect(chip?.querySelector("svg")).toBeNull();
  });
});
