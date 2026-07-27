import { afterEach, describe, expect, it, vi } from "vitest";
import { detailScanResponseSchema, graphEdgeSchema, graphNodeSchema } from "../types";
import {
  createDetailScan,
  detailScanRequest,
  targetForEdge,
  targetForNode,
  targetForTrace,
  viewerPayloadFromDetailScan,
} from "./detailScanApi";

function responseFixture() {
  const graph = {
    project_id: "project:p1",
    scan_id: "scan:s1",
    build_id: "build:child",
    environment_id: "environment:default-static",
    generated_from_build_id: "build:child",
    nodes: [],
    edges: [],
    details: { evidence_by_id: {}, risk_hints_by_id: {} },
    filters: { available: [], lenses: [] },
  };
  const map = {
    schema_version: "ai-system-map/v2",
    scan_id: "scan:s1",
    build_id: "build:child",
    generated_from_build_id: "build:child",
    project: { project_id: "project:p1" },
  };
  return {
    project_id: "project:p1",
    source_build_id: "build:base",
    build_id: "build:child",
    scan_id: "scan:s1",
    warnings: [],
    detail_scan: {
      id: "detail-scan:component:component_instance:router",
      target_type: "component_instance",
      target: "component:router",
      scan_depth: "component",
      status: "completed",
      findings: [],
      code_path: [],
      warnings: [],
      best_effort: true,
      context_limits: {},
    },
    ai_system_map: map,
    viewer_load_result: {
      loaded: true,
      ai_system_map: map,
      graph_view_model: graph,
    },
  };
}

describe("Detail Scan API contract", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("always sends current project/build identity to the current endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseFixture()), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const target = { targetType: "component_instance" as const, target: "component:router", label: "Router" };

    await createDetailScan("http://127.0.0.1:8000/", detailScanRequest("project:p1", "build:base", target, "component"));

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/api/detail-scans");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      project_id: "project:p1",
      build_id: "build:base",
      target_type: "component_instance",
      target: "component:router",
      scan_depth: "component",
    });
  });

  it("uses only backend-declared canonical identity fields", () => {
    const component = graphNodeSchema.parse({
      id: "node:component:router",
      source_id: "component:wrong-display-source",
      component_id: "component:router",
      semantic_kind: "repo_component",
      label: "Looks like an extension",
      badges: ["extension", "unmapped"],
    });
    const reference = graphNodeSchema.parse({
      id: "reference:router",
      source_id: "component:tempting-prefix",
      semantic_kind: "reference_capability",
      label: "Router",
    });
    const edge = graphEdgeSchema.parse({
      id: "graph:edge:retrieval",
      source_id: "edge:retrieval",
      from: "node:a",
      to: "node:b",
    });

    expect(targetForNode(component)).toMatchObject({ targetType: "component_instance", target: "component:router" });
    expect(targetForNode(reference)).toBeNull();
    expect(targetForEdge(edge)).toMatchObject({ targetType: "edge", target: "edge:retrieval" });
    expect(targetForTrace({
      id: "trace:1",
      sequence_index: 0,
      timestamp: "2026-07-21T00:00:00Z",
      warnings: [],
      evidence_id: "evidence:safe",
    })).toMatchObject({
      targetType: "evidence",
      target: "evidence:safe",
    });
  });

  it("rejects Windows, UNC, absolute and traversal paths in L3 responses", () => {
    for (const file of ["C:\\repo\\app.py", "\\\\server\\repo\\app.py", "/repo/app.py", "src/../secret.py"]) {
      const fixture = responseFixture();
      fixture.detail_scan.scan_depth = "code_path";
      fixture.detail_scan.code_path = [{ file }] as never[];
      expect(detailScanResponseSchema.safeParse(fixture).success).toBe(false);
    }
    const fixture = responseFixture();
    fixture.detail_scan.scan_depth = "code_path";
    fixture.detail_scan.code_path = [{ file: "src/app.py", symbol: "main", line_start: 4, line_end: 8 }] as never[];
    expect(detailScanResponseSchema.safeParse(fixture).success).toBe(true);
  });

  it("normalizes the POST child projection without using session latest", () => {
    const payload = viewerPayloadFromDetailScan(detailScanResponseSchema.parse(responseFixture()));
    expect(payload.viewer_load_result.project_id).toBe("project:p1");
    expect(payload.viewer_load_result.build_id).toBe("build:child");
    expect(payload.viewer_load_result.based_on_build_id).toBe("build:base");
  });

  it("rejects an unbound or mismatched fallback projection", () => {
    const missingGraphIdentity = responseFixture();
    missingGraphIdentity.viewer_load_result.graph_view_model = {
      ...missingGraphIdentity.viewer_load_result.graph_view_model,
      build_id: undefined,
    } as never;
    expect(() => viewerPayloadFromDetailScan(detailScanResponseSchema.parse(missingGraphIdentity))).toThrow(
      /Child graph build_id/,
    );

    const mismatchedMap = responseFixture();
    mismatchedMap.viewer_load_result.ai_system_map = {
      ...mismatchedMap.viewer_load_result.ai_system_map,
      build_id: "build:other",
    };
    expect(() => viewerPayloadFromDetailScan(detailScanResponseSchema.parse(mismatchedMap))).toThrow(
      /Child viewer map identity/,
    );
  });
});
