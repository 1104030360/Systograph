import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { graphViewModelSchema, viewerPayloadSchema } from "../types";
import { useViewerStore } from "../store/viewerStore";
import { DetailPanel } from "./DetailPanel";

const detailScanMock = vi.hoisted(() => vi.fn());
vi.mock("../hooks/useDetailScan", () => ({ useDetailScan: detailScanMock }));

function defaultDetailScanState() {
  return {
    run: vi.fn(),
    reset: vi.fn(),
    data: undefined,
    results: [],
    variables: undefined,
    requestBuildId: null,
    isPending: false,
    isSuccess: false,
    error: undefined,
    isStaleBase: false,
    refreshCurrentBuild: vi.fn(),
  };
}

const graph = graphViewModelSchema.parse({
  nodes: [
    {
      id: "node:coordinator",
      label: "Coordinator",
      plane_id: "control",
      semantic_kind: "reference_capability",
      reference_node_id: "planner",
      status: "conflicted",
      activation: "conflicted",
      conflict_fields: [{ field: "status", reason: "Evidence disagrees" }],
      assessment_scope: {
        build_id: "build:b2",
        scan_id: "scan:s1",
        environment_id: "environment:static",
      },
      related_component_ids: ["component:agent"],
      direct_evidence_ids: ["evidence:planner"],
      uncertainty: "Runtime execution is not verified.",
      recommended_next_checks: ["Run a bounded runtime trace."],
    },
    { id: "node:legacy", label: "Legacy component" },
    { id: "node:frontier", label: "Frontier component", plane_id: "trust_boundary" },
    {
      id: "node:repo-router",
      label: "Project router",
      semantic_kind: "repo_component",
      source_id: "component:router",
      component_id: "component:router",
      evidence_ids: ["evidence:router"],
    },
  ],
  edges: [],
  relationships: [
    {
      id: "relationship:planner-agent",
      kind: "reference_component_mapping",
      source_node_id: "node:coordinator",
      target_node_id: "node:legacy",
      evidence_ids: [],
    },
  ],
  details: {
    evidence_by_id: {
      "evidence:router": { title: "Router declaration", file: "src/router.py", value: "raw-secret-value" },
    },
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

const currentPayload = viewerPayloadSchema.parse({
  contract_source: "phase2-build",
  viewer_load_result: {
    loaded: true,
    project_id: "project:p1",
    scan_id: "scan:s1",
    build_id: "build:b2",
    environment_id: "environment:static",
    generated_from_build_id: "build:b2",
    ai_system_map: { schema_version: "ai-system-map/v2" },
    profile_inference_result: null,
    readiness_report: null,
    graph_view_model: graph,
  },
});

function renderPanel(
  nodeId: string,
  detailMode: "overview" | "evidence" | "code_path" = "overview",
  viewerPayload = payload,
  onDetailModeChange = vi.fn(),
) {
  return render(
    <DetailPanel
      graph={graph}
      payload={viewerPayload}
      selected={{ kind: "node", id: nodeId }}
      detailMode={detailMode}
      onDetailModeChange={onDetailModeChange}
      onClose={() => {}}
    />,
  );
}

describe("DetailPanel plane chip", () => {
  beforeEach(() => {
    detailScanMock.mockReset();
    detailScanMock.mockReturnValue(defaultDetailScanState());
    useViewerStore.setState({
      dataSourceMode: "api",
      apiBaseUrl: "http://127.0.0.1:8000",
      activeProjectId: "project:p1",
      activeBuildId: null,
    });
  });
  it("shows an icon plus text label when the backend published plane_id", () => {
    const { container } = renderPanel("node:coordinator");

    const chip = container.querySelector(".plane-chip");
    expect(chip).not.toBeNull();
    expect(chip).toHaveTextContent("Control");
    const icon = chip?.querySelector(".prototype-icon-control");
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
    expect(chip?.querySelector(".prototype-icon")).toBeNull();
  });

  it("surfaces backend assessment scope, typed evidence, conflicts, and next checks", () => {
    renderPanel("node:coordinator", "evidence");

    expect(screen.getByText("Reference Capability")).toBeInTheDocument();
    expect(screen.getByText(/environment:static/)).toBeInTheDocument();
    expect(screen.getByText(/evidence:planner/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence disagrees/)).toBeInTheDocument();
    expect(screen.getByText(/Runtime execution is not verified/)).toBeInTheDocument();
    expect(screen.getByText(/Run a bounded runtime trace/)).toBeInTheDocument();
  });

  it("keeps the summary compact and moves long identifiers behind a disclosure", () => {
    const { container } = renderPanel("node:coordinator");

    expect(screen.getByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Assessment")).toBeInTheDocument();
    expect(screen.getByText("Activation")).toBeInTheDocument();
    expect(screen.getByText(/Identifiers/)).toBeInTheDocument();
    expect(container.querySelector(".detail-disclosure")).not.toHaveAttribute("open");
    expect(container.querySelector(".inspector-sub")).toBeNull();
  });

  it("runs L2 with backend-declared component identity and supports evidence drill-down", () => {
    const run = vi.fn();
    const onDetailModeChange = vi.fn();
    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      run,
      isSuccess: true,
      variables: {
        target: { targetType: "component_instance", target: "component:router", label: "Project router" },
        scanDepth: "component",
      },
      requestBuildId: "build:b1",
      data: {
        response: {
          project_id: "project:p1",
          source_build_id: "build:b1",
          build_id: "build:b2",
          detail_scan: {
            id: "detail:router",
            target_type: "component_instance",
            target: "component:router",
            scan_depth: "component",
            status: "completed",
            findings: [{ kind: "setting", summary: "Router is configured.", evidence_ids: ["evidence:router"] }],
            code_path: [],
            warnings: [],
            context_limits: { files_considered: 1 },
          },
        },
      },
      results: [
        {
          response: {
            project_id: "project:p1",
            source_build_id: "build:b1",
            build_id: "build:b2",
            detail_scan: {
              id: "detail:router",
              target_type: "component_instance",
              target: "component:router",
              scan_depth: "component",
              status: "completed",
              findings: [{ kind: "setting", summary: "Router is configured.", evidence_ids: ["evidence:router"] }],
              code_path: [],
              warnings: [],
              context_limits: { files_considered: 1 },
            },
          },
        },
      ],
    });

    renderPanel("node:repo-router", "evidence", currentPayload, onDetailModeChange);
    expect(screen.getByText("Router is configured.")).toBeInTheDocument();
    expect(screen.queryByText("raw-secret-value")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /src\/router.py/i }));
    expect(onDetailModeChange).toHaveBeenCalledWith("code_path");
    fireEvent.click(screen.getByRole("button", { name: "Run again" }));
    expect(run).toHaveBeenCalledWith({
      target: { targetType: "component_instance", target: "component:router", label: "Project router" },
      scanDepth: "component",
    });
  });

  it("renders loading, empty, partial and retry states without clearing the graph", () => {
    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      isPending: true,
      variables: {
        target: { targetType: "component_instance", target: "component:router", label: "Project router" },
        scanDepth: "component",
      },
      requestBuildId: "build:b2",
    });
    const loading = renderPanel("node:repo-router", "evidence", currentPayload);
    expect(screen.getByText(/Running bounded scan/)).toBeInTheDocument();
    loading.unmount();

    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      variables: {
        target: { targetType: "component_instance", target: "component:router", label: "Project router" },
        scanDepth: "component",
      },
      data: {
        response: {
          project_id: "project:p1",
          build_id: "build:b2",
          detail_scan: {
            id: "detail:empty",
            target_type: "component_instance",
            target: "component:router",
            scan_depth: "component",
            status: "partial",
            findings: [],
            code_path: [],
            warnings: ["bounded_context"],
            context_limits: {},
          },
        },
      },
      results: [
        {
          response: {
            project_id: "project:p1",
            build_id: "build:b2",
            detail_scan: {
              id: "detail:empty",
              target_type: "component_instance",
              target: "component:router",
              scan_depth: "component",
              status: "partial",
              findings: [],
              code_path: [],
              warnings: ["bounded_context"],
              context_limits: {},
            },
          },
        },
      ],
    });
    const partial = renderPanel("node:repo-router", "evidence", currentPayload);
    expect(screen.getByText(/partial bounded result/i)).toBeInTheDocument();
    expect(screen.getByText(/without additional bounded findings/i)).toBeInTheDocument();
    partial.unmount();

    const run = vi.fn();
    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      run,
      variables: {
        target: { targetType: "component_instance", target: "component:router", label: "Project router" },
        scanDepth: "component",
      },
      requestBuildId: "build:b2",
      error: "target_not_found",
    });
    renderPanel("node:repo-router", "evidence", currentPayload);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(run).toHaveBeenCalledOnce();
  });

  it("renders stale-base and immutable historical-build states", () => {
    const refreshCurrentBuild = vi.fn();
    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      variables: {
        target: { targetType: "component_instance", target: "component:router", label: "Project router" },
        scanDepth: "component",
      },
      requestBuildId: "build:b2",
      error: "base_build_not_latest",
      isStaleBase: true,
      refreshCurrentBuild,
    });
    const stale = renderPanel("node:repo-router", "evidence", currentPayload);
    fireEvent.click(screen.getByRole("button", { name: /Reload current build/ }));
    expect(refreshCurrentBuild).toHaveBeenCalledOnce();
    stale.unmount();

    useViewerStore.setState({ activeBuildId: "build:b2" });
    renderPanel("node:repo-router", "evidence", currentPayload);
    expect(screen.getByText(/Historical builds are immutable/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Run L2/ })).not.toBeInTheDocument();
  });

  it("renders only backend-provided project-relative L3 hops and uncertainty", () => {
    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      variables: {
        target: { targetType: "component_instance", target: "component:router", label: "Project router" },
        scanDepth: "code_path",
      },
      data: {
        response: {
          project_id: "project:p1",
          build_id: "build:b2",
          detail_scan: {
            id: "detail:path",
            target_type: "component_instance",
            target: "component:router",
            scan_depth: "code_path",
            status: "completed",
            findings: [],
            code_path: [
              { file: "src/router.py", symbol: "route_query", line_start: 12, line_end: 18, best_effort: true },
            ],
            warnings: ["bounded_static_path"],
            context_limits: {},
          },
        },
      },
      results: [
        {
          response: {
            project_id: "project:p1",
            source_build_id: "build:b1",
            build_id: "build:b2",
            detail_scan: {
              id: "detail:path",
              target_type: "component_instance",
              target: "component:router",
              scan_depth: "code_path",
              status: "completed",
              findings: [],
              code_path: [
                { file: "src/router.py", symbol: "route_query", line_start: 12, line_end: 18, best_effort: true },
              ],
              warnings: ["bounded_static_path"],
              context_limits: {},
            },
          },
        },
      ],
    });

    renderPanel("node:repo-router", "code_path", currentPayload);
    expect(screen.getByText("route_query")).toBeInTheDocument();
    expect(screen.getByText("src/router.py:12–18")).toBeInTheDocument();
    expect(screen.getByText(/not runtime traversal proof/i)).toBeInTheDocument();
    expect(screen.getByText(/project-relative POSIX paths on both Windows and macOS/i)).toBeInTheDocument();
  });

  it("keeps an L2 result visible along the locally proven L3 child lineage", () => {
    const childPayload = viewerPayloadSchema.parse({
      ...currentPayload,
      viewer_load_result: {
        ...currentPayload.viewer_load_result,
        build_id: "build:b3",
        generated_from_build_id: "build:b3",
        graph_view_model: {
          ...currentPayload.viewer_load_result.graph_view_model,
          build_id: "build:b3",
          generated_from_build_id: "build:b3",
        },
      },
    });
    detailScanMock.mockReturnValue({
      ...defaultDetailScanState(),
      results: [
        {
          response: {
            project_id: "project:p1",
            source_build_id: "build:b1",
            build_id: "build:b2",
            detail_scan: {
              id: "detail:l2",
              target_type: "component_instance",
              target: "component:router",
              scan_depth: "component",
              status: "completed",
              findings: [{ kind: "setting", summary: "Preserved L2 result.", evidence_ids: [] }],
              code_path: [],
              warnings: [],
              context_limits: {},
            },
          },
        },
        {
          response: {
            project_id: "project:p1",
            source_build_id: "build:b2",
            build_id: "build:b3",
            detail_scan: {
              id: "detail:l3",
              target_type: "component_instance",
              target: "component:router",
              scan_depth: "code_path",
              status: "completed",
              findings: [],
              code_path: [],
              warnings: [],
              context_limits: {},
            },
          },
        },
      ],
    });

    renderPanel("node:repo-router", "evidence", childPayload);
    expect(screen.getByText("Preserved L2 result.")).toBeInTheDocument();
  });

  it("does not invent a target for reference capabilities", () => {
    renderPanel("node:coordinator", "evidence", currentPayload);
    expect(screen.getByText(/does not publish a supported canonical Detail Scan target/)).toBeInTheDocument();
  });
});
