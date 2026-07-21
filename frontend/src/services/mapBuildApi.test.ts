import { afterEach, describe, expect, it, vi } from "vitest";
import { applyConfirmedMappings } from "./mapBuildApi";

function buildResponse(baseBuildId = "build:b1", buildId = "build:b2") {
  const map = {
    schema_version: "ai-system-map/v2",
    system_type: "ai_system",
    scan_id: "scan:s1",
    build_id: buildId,
    environment_id: "environment:default-static",
    generated_from_build_id: buildId,
    project: { project_id: "project:p1", name: "demo", root_path: null, path_mode: "redacted" },
    components: [], edges: [], evidence: [], endpoints: [], risk_hints: [], unmapped_components: [],
  };
  const graph = {
    schema_version: "graph-view-model/v1",
    source_schema_version: "ai-system-map/v2",
    project_id: "project:p1",
    scan_id: "scan:s1",
    build_id: buildId,
    environment_id: "environment:default-static",
    generated_from_build_id: buildId,
    reference_map_version: "1",
    nodes: [],
    edges: [],
    details: {
      evidence_by_id: {}, risk_hints_by_id: {}, reference_assessments_by_id: {},
      profile_findings_by_id: {}, capability_candidates_by_id: {},
    },
    filters: { available: [], lenses: [] },
  };
  return {
    project_id: "project:p1",
    scan_id: "scan:s1",
    build_id: buildId,
    based_on_build_id: baseBuildId,
    build_reason: "apply_confirmations",
    applied_mapping_ids: ["mapping:m1"],
    build_result: {
      status: "ok",
      project_name: "demo",
      active_schema_version: "ai-system-map/v2",
      requested_schema_version: "ai-system-map/v2",
      source_schema_version: "ai-system-map/v2",
      operator_rollback_active: false,
      migration_warnings: [],
      warnings: [],
      profile_signals_available: false,
      readiness_report_available: false,
      profile_inference_result: null,
      readiness_report: null,
    },
    viewer_load_result: {
      loaded: true,
      error_reason: null,
      ai_system_map: map,
      graph_view_model: graph,
    },
  };
}

describe("map build apply API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("applies exact durable mapping ids to the requested base build", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(buildResponse()), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await applyConfirmedMappings("http://127.0.0.1:8000", "build:b1", ["mapping:m1"]);
    expect(response.build_id).toBe("build:b2");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/map-builds/build%3Ab1/apply");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ mapping_ids: ["mapping:m1"] });
  });

  it("rejects a response that does not descend from the requested base", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify(buildResponse("build:other")), { status: 200 }),
    ));
    await expect(applyConfirmedMappings("http://127.0.0.1:8000", "build:b1", ["mapping:m1"]))
      .rejects.toThrow(/requested base build/);
  });
});
