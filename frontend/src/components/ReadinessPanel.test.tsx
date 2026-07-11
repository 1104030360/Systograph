import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { graphViewModelSchema } from "../types";
import { ReadinessPanel } from "./ReadinessPanel";

const graph = graphViewModelSchema.parse({
  nodes: [{ id: "node:component:retriever:qdrant", source_id: "component:retriever:qdrant", label: "Retriever" }],
  edges: [],
  details: {
    evidence_by_id: { "evidence:prompt-context": { title: "Prompt context assembly" } },
    risk_hints_by_id: {},
    profile_findings_by_id: {},
    capability_candidates_by_id: {},
  },
  filters: { available: [], lenses: [] },
});

const report = {
  schema_version: "readiness-report/v1",
  source_schema_version: "ai-system-map/v2",
  project_id: "project:sample",
  scan_id: "scan:sample",
  build_id: "build:sample",
  environment_id: "environment:default-static",
  generated_from_build_id: "build:sample",
  finding_registry_version: "readiness-findings/v1",
  release_verdict: "needs_review",
  summary: { status: "partial", runtime_verified: false, evidence_scope: ["capability:retrieval"] },
  findings: [
    {
      finding_id: "finding:source-traceability-not-detected",
      category: "source_traceability",
      title: "Source traceability not detected",
      severity: "medium",
      status: "not_detected",
      description: "No citation mapping detected in the final answer.",
      affected_component_ids: ["component:retriever:qdrant", "component:not-projected"],
      evidence_ids: ["evidence:prompt-context"],
      recommended_next_checks: ["Check whether retriever output preserves source metadata."],
      limitations: ["Static analysis cannot observe runtime formatters."],
    },
  ],
};

describe("ReadinessPanel", () => {
  it("renders backend verdict, five-state chips, and next checks", () => {
    render(<ReadinessPanel report={report} graph={graph} onSelectComponent={() => {}} onClose={() => {}} />);

    expect(screen.getByText("Needs Review")).toBeInTheDocument();
    expect(screen.getByText("Source traceability not detected")).toBeInTheDocument();
    expect(screen.getByText("Not Detected")).toBeInTheDocument();
    expect(screen.getByText(/not runtime verified/)).toBeInTheDocument();
    expect(screen.getByText("Check whether retriever output preserves source metadata.")).toBeInTheDocument();
    expect(screen.getByText("Prompt context assembly")).toBeInTheDocument();
  });

  it("drills down to a projected component and leaves unprojected refs inert", () => {
    const onSelectComponent = vi.fn();
    render(<ReadinessPanel report={report} graph={graph} onSelectComponent={onSelectComponent} onClose={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "component:retriever:qdrant" }));
    expect(onSelectComponent).toHaveBeenCalledWith("node:component:retriever:qdrant");

    expect(screen.queryByRole("button", { name: "component:not-projected" })).not.toBeInTheDocument();
    expect(screen.getByText("component:not-projected")).toBeInTheDocument();
  });

  it("explains a missing report instead of fabricating findings", () => {
    render(<ReadinessPanel report={null} graph={graph} onSelectComponent={() => {}} onClose={() => {}} />);

    expect(screen.getByText(/does not include a readiness report/)).toBeInTheDocument();
  });

  it("degrades on an unsupported report contract", () => {
    render(
      <ReadinessPanel
        report={{ schema_version: "readiness-report/v99" }}
        graph={graph}
        onSelectComponent={() => {}}
        onClose={() => {}}
      />,
    );

    expect(screen.getByText(/contract this viewer version does not support/)).toBeInTheDocument();
  });
});
