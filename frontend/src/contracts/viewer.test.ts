import { describe, expect, it } from "vitest";
import phase2ViewerSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-08-viewer/frontend-json-sample.json";
import legacyViewerSample from "../data/frontend-json-sample.json";
import {
  extractMappingCompleteness,
  parseMapBuildPayload,
  parseViewerPayload,
  phase2ViewerLoadResultSchema,
} from "./viewer";

/* Mimics kai_mind.web.schemas.MapBuildScopedResponse: phase2 lineage +
   validated sidecars (reused from the handoff sample so identities are real)
   around a v1 base graph projection. */
function mapBuildResponseFixture() {
  return {
    project_id: "project:sample-ai-health-rag",
    scan_id: "scan:sample-s1",
    build_id: "build:sample-b2",
    based_on_build_id: null,
    build_reason: "initial_scan",
    applied_mapping_ids: [],
    build_result: {
      status: "ok",
      project_name: "sample-ai-health-rag",
      active_schema_version: "ai-system-map/v1",
      requested_schema_version: "ai-system-map/v1",
      migration_warnings: ["v1_projection_active"],
      warnings: ["profile_signals_missing_or_invalid"],
      profile_signals_available: true,
      readiness_report_available: true,
      profile_inference_result: structuredClone(phase2ViewerSample.profile_inference_result) as Record<
        string,
        unknown
      > | null,
      readiness_report: structuredClone(phase2ViewerSample.readiness_report) as Record<string, unknown> | null,
    },
    viewer_load_result: {
      loaded: true,
      error_reason: null,
      ai_system_map: { schema_version: "ai-system-map/v1", scan_summary: { status: "ok" } },
      graph_view_model: {
        nodes: [{ id: "node:api", label: "API", status: "detected" }],
        edges: [],
        details: {
          evidence_by_id: {},
          risk_hints_by_id: {},
          profile_findings_by_id: {},
          capability_candidates_by_id: {},
        },
        filters: { available: [], lenses: [] },
      },
    },
  };
}

describe("viewer contract parsing", () => {
  it("parses the Phase 2 handoff sample without losing build-scoped fields", () => {
    const parsed = phase2ViewerLoadResultSchema.parse(phase2ViewerSample);
    const normalized = parseViewerPayload(phase2ViewerSample);

    expect(normalized.contract_source).toBe("phase2");
    expect(normalized.viewer_load_result.build_id).toBe("build:sample-b2");
    expect(normalized.viewer_load_result.artifact_refs).toHaveLength(10);
    expect(normalized.viewer_load_result.graph_view_model.mapping_completeness?.denominator).toBe(52);
    expect(normalized.viewer_load_result.graph_view_model.nodes[0].activation).toBe("enabled");
    expect(normalized.viewer_load_result.graph_view_model.nodes[0].semantic_kind).toBe("canonical_component");
    expect(parsed.profile_inference_result?.reference_capability_assessments).toHaveLength(52);
    expect(parsed.profile_inference_result?.profiles).toHaveLength(15);
    expect(parsed.profile_inference_result?.reference_capability_assessments[0].plane_id).toBe("input_intent");
    expect(parsed.readiness_report?.grounding.applicability).toBe("undetermined");
    expect(parsed.readiness_report?.findings.length).toBeGreaterThan(0);
  });

  it("adapts the current legacy ViewerPayload to the same frontend shape", () => {
    const normalized = parseViewerPayload(legacyViewerSample);

    expect(normalized.contract_source).toBe("legacy-v1");
    expect(normalized.viewer_load_result.loaded).toBe(true);
    expect(normalized.viewer_load_result.build_id).toBeNull();
    expect(normalized.viewer_load_result.warnings).toEqual([]);
    expect(normalized.viewer_load_result.artifact_refs).toEqual([]);
    expect(normalized.viewer_load_result.profile_inference_result).toBeNull();
    expect(normalized.viewer_load_result.graph_view_model.nodes.length).toBeGreaterThan(0);
  });

  it("rejects cross-build inline artifacts", () => {
    const invalid = structuredClone(phase2ViewerSample);
    invalid.graph_view_model.build_id = "build:other";

    expect(() => parseViewerPayload(invalid)).toThrow(/graph_view_model\.build_id must match/);
  });

  it("rejects artifact refs that expose a path instead of a basename", () => {
    const invalid = structuredClone(phase2ViewerSample);
    invalid.artifact_refs[0].file_name = "C:\\private\\ai_system_map.json";

    expect(() => parseViewerPayload(invalid)).toThrow(/file_name must be a basename/);
  });
});

describe("map build scoped parsing", () => {
  it("normalizes the current build-scoped response with lineage and sidecars", () => {
    const normalized = parseMapBuildPayload(mapBuildResponseFixture());
    const result = normalized.viewer_load_result;

    expect(normalized.contract_source).toBe("phase2-build");
    expect(result.loaded).toBe(true);
    expect(result.project_id).toBe("project:sample-ai-health-rag");
    expect(result.scan_id).toBe("scan:sample-s1");
    expect(result.build_id).toBe("build:sample-b2");
    expect(result.environment_id).toBe("environment:default-static");
    expect(result.warnings).toEqual(["profile_signals_missing_or_invalid", "v1_projection_active"]);
    expect(result.artifact_refs).toEqual([]);
    expect(result.profile_inference_result).not.toBeNull();
    expect(result.readiness_report).not.toBeNull();
    expect(result.graph_view_model.nodes).toHaveLength(1);
  });

  it("rejects a sidecar from a different build", () => {
    const invalid = mapBuildResponseFixture();
    if (!invalid.build_result.readiness_report) throw new Error("fixture requires a readiness report");
    invalid.build_result.readiness_report.build_id = "build:other";

    expect(() => parseMapBuildPayload(invalid)).toThrow(/readiness_report\.build_id must match/);
  });

  it("degrades to null identity extras when sidecars are absent", () => {
    const fixture = mapBuildResponseFixture();
    fixture.build_result.profile_inference_result = null;
    fixture.build_result.readiness_report = null;
    fixture.build_result.profile_signals_available = false;
    fixture.build_result.readiness_report_available = false;

    const normalized = parseMapBuildPayload(fixture);
    expect(normalized.viewer_load_result.environment_id).toBeNull();
    expect(normalized.viewer_load_result.build_id).toBe("build:sample-b2");
  });
});

describe("extractMappingCompleteness", () => {
  it("prefers the graph projection value and falls back to the profile sidecar", () => {
    const target = parseViewerPayload(phase2ViewerSample);
    expect(extractMappingCompleteness(target)?.denominator).toBe(52);

    const buildScoped = parseMapBuildPayload(mapBuildResponseFixture());
    expect(buildScoped.viewer_load_result.graph_view_model.mapping_completeness).toBeUndefined();
    expect(extractMappingCompleteness(buildScoped)?.denominator).toBe(52);
  });

  it("returns undefined instead of fabricating a value", () => {
    const fixture = mapBuildResponseFixture();
    fixture.build_result.profile_inference_result = null;

    expect(extractMappingCompleteness(parseMapBuildPayload(fixture))).toBeUndefined();
  });
});
