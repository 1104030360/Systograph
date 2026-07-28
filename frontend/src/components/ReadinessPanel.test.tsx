import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { graphViewModelSchema } from "../types";
import { ReadinessPanel } from "./ReadinessPanel";

const graph = graphViewModelSchema.parse({
  nodes: [],
  edges: [],
  details: {
    evidence_by_id: { "evidence:prompt-context": { title: "Prompt context assembly" } },
    risk_hints_by_id: {},
    profile_findings_by_id: {},
    capability_candidates_by_id: {},
  },
  filters: { available: [], lenses: [] },
});

/* Shape mirrors systograph.core.models.readiness_report.ReadinessReport. */
const report = {
  schema_version: "readiness-report/v1",
  source_schema_version: "ai-system-map/v2",
  scan_id: "scan:sample",
  build_id: "build:sample",
  environment_id: "environment:default-static",
  generated_from_build_id: "build:sample",
  mapping_completeness: {
    numerator: 4,
    denominator: 52,
    value: 0.076923,
    weights: { detected: 1, partial: 0.5, undetermined: 0, not_detected: 1, conflicted: 0 },
  },
  grounding: {
    applicability: "undetermined",
    status: "undetermined",
    dimensions: [],
    evidence_ids: [],
    reason: "Scanner coverage is insufficient to prove absence.",
  },
  capability_summaries: [],
  findings: [
    {
      finding_id: "readiness:profile:rag-grounding",
      category: "capability_readiness",
      status: "undetermined",
      title: "Capability readiness: rag-grounding",
      reason: "Scanner coverage is insufficient to prove absence.",
      evidence_ids: ["evidence:prompt-context"],
      recommended_next_checks: ["Review the missing deterministic capability signals."],
    },
  ],
  recommended_next_checks: ["Run a detail scan on the retrieval components."],
  limitations: ["Static analysis does not prove runtime behavior."],
  primary_map_type: "agentic_ai_system",
};

describe("ReadinessPanel", () => {
  it("renders backend grounding summary, five-state chips, and next checks", () => {
    render(<ReadinessPanel report={report} graph={graph} onClose={() => {}} />);

    expect(screen.getByRole("dialog", { name: "Readiness" })).toBeInTheDocument();
    expect(screen.getAllByText("Undetermined").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Grounding" })).toBeInTheDocument();
    expect(screen.getByText("Capability readiness: rag-grounding")).toBeInTheDocument();
    expect(screen.getByText("Review the missing deterministic capability signals.")).toBeInTheDocument();
    expect(screen.getByText("Run a detail scan on the retrieval components.")).toBeInTheDocument();
    expect(screen.getByText("Prompt context assembly")).toBeInTheDocument();
    expect(screen.getByText(/Static analysis does not prove runtime behavior/)).toBeInTheDocument();
  });

  it("explains a missing report instead of fabricating findings", () => {
    render(<ReadinessPanel report={null} graph={graph} onClose={() => {}} />);

    expect(screen.getByText(/does not include a readiness report/)).toBeInTheDocument();
    expect(screen.getByText(/UI example only/)).toBeInTheDocument();
    expect(screen.getByText(/not a scan result/)).toBeInTheDocument();
  });

  it("switches to safe plain-text Markdown source", () => {
    render(<ReadinessPanel report={report} graph={graph} onClose={() => {}} />);

    fireEvent.click(screen.getByRole("tab", { name: "Generated Markdown" }));

    expect(screen.getByText(/^# Readiness report/)).toBeInTheDocument();
    expect(screen.getByText(/build:sample/)).toBeInTheDocument();
    expect(screen.getByText(/generated from the inline/)).toBeInTheDocument();
    expect(screen.getByText(/No standalone Markdown artifact preview or download/)).toBeInTheDocument();
  });

  it("degrades on an unsupported report contract", () => {
    render(<ReadinessPanel report={{ schema_version: "readiness-report/v99" }} graph={graph} onClose={() => {}} />);

    expect(screen.getByText(/contract this viewer version does not support/)).toBeInTheDocument();
  });

  it("closes with Escape", () => {
    const onClose = vi.fn();
    render(<ReadinessPanel report={report} graph={graph} onClose={onClose} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalledOnce();
  });
});
