import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { graphViewModelSchema } from "../types";
import { ArchitectureInfoDialog } from "./ArchitectureInfoDialog";

const graph = graphViewModelSchema.parse({
  schema_version: "graph-view-model/v2",
  source_schema_version: "ai-system-map/v2",
  scan_id: "scan:sample",
  build_id: "build:sample",
  environment_id: "environment:default-static",
  nodes: [],
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

describe("ArchitectureInfoDialog", () => {
  it("moves the architecture guide and contract metadata into a dialog", () => {
    render(<ArchitectureInfoDialog graph={graph} onClose={() => {}} />);

    expect(screen.getByRole("dialog", { name: "How to read this map" })).toBeInTheDocument();
    expect(screen.getByText("Why ten planes?")).toBeInTheDocument();
    expect(screen.getByText("Status is not activation")).toBeInTheDocument();
    expect(screen.getByText("Backend membership only")).toBeInTheDocument();
    expect(screen.getByText("ai-system-map/v2")).toBeInTheDocument();
    expect(screen.getByText("build:sample")).toBeInTheDocument();
  });

  it("closes with Escape", () => {
    const onClose = vi.fn();
    render(<ArchitectureInfoDialog graph={graph} onClose={onClose} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalledOnce();
  });
});
