import { describe, expect, it } from "vitest";
import phase2ViewerSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-08-viewer/frontend-json-sample.json";
import legacyViewerSample from "../data/frontend-json-sample.json";
import {
  extractMappingCompleteness,
  parseMapBuildPayload,
  parseViewerPayload,
  phase2ViewerLoadResultSchema,
} from "./viewer";

function plan06GraphProjectionFixture() {
  const lens = (id: string, label: string) => ({
    id,
    label,
    supported: true,
    unavailable_reason: null,
    matches_node_ids: ["reference:planner", "component:agent"],
    matches_edge_ids: ["edge:agent-flow"],
  });

  return {
    schema_version: "graph-view-model/v1",
    // PR #250 projects a normalized v2 view even while the active artifact is
    // still v1, so plane presentation must not key off this field alone.
    source_schema_version: "ai-system-map/v1",
    project_id: "project:sample-ai-health-rag",
    scan_id: "scan:sample-s1",
    build_id: "build:sample-b2",
    environment_id: "environment:default-static",
    generated_from_build_id: "build:sample-b2",
    reference_map_version: "1",
    mapping_completeness: {
      numerator: 40,
      denominator: 52,
      value: 40 / 52,
      weights: { detected: 1, partial: 0.5, undetermined: 0, not_detected: 1, conflicted: 0 },
    },
    map_json: "ai_system_map.json",
    summary: { reference_node_count: 52 },
    nodes: [
      {
        id: "reference:planner",
        source_id: null,
        reference_node_id: "planner",
        component_id: null,
        profile_id: null,
        plane_id: "control",
        type: "reference_capability",
        semantic_kind: "reference_capability",
        slot: null,
        status: "conflicted",
        activation: "conflicted",
        label: "Planner",
        subtitle: null,
        badges: [],
        evidence_ids: ["evidence:planner"],
        direct_evidence_ids: ["evidence:planner"],
        indirect_evidence_ids: [],
        explicit_negative_evidence_ids: [],
        conflict_fields: [{ field: "status", reason: "positive and negative evidence disagree" }],
        not_detected_coverage_gate_passed: null,
        assessment_scope: {
          build_id: "build:sample-b2",
          scan_id: "scan:sample-s1",
          environment_id: "environment:default-static",
        },
        primary_anchor_node_id: null,
        anchor_node_ids: [],
        related_component_ids: ["component:agent"],
        related_unmapped_component_ids: [],
        related_capability_candidate_component_ids: [],
        related_risk_hint_ids: [],
        description: "Plans the agent workflow.",
        implementation_depth_level: 2,
        implementation_depth_reason: "Static control flow is present.",
        evidence_strength: "direct",
        uncertainty: "Runtime execution is not verified.",
        recommended_next_checks: ["Run a bounded runtime trace."],
        risk_hint_ids: [],
      },
      {
        id: "component:agent",
        source_id: "component:agent",
        reference_node_id: null,
        component_id: "component:agent",
        profile_id: null,
        plane_id: "control",
        type: "agent",
        semantic_kind: "repo_component",
        slot: null,
        status: null,
        activation: null,
        label: "Agent",
        subtitle: null,
        badges: [],
        evidence_ids: ["evidence:agent"],
        direct_evidence_ids: [],
        indirect_evidence_ids: [],
        explicit_negative_evidence_ids: [],
        conflict_fields: [],
        not_detected_coverage_gate_passed: null,
        assessment_scope: null,
        primary_anchor_node_id: null,
        anchor_node_ids: [],
        related_component_ids: [],
        related_unmapped_component_ids: [],
        related_capability_candidate_component_ids: [],
        related_risk_hint_ids: [],
        description: null,
        implementation_depth_level: null,
        implementation_depth_reason: null,
        evidence_strength: null,
        uncertainty: null,
        recommended_next_checks: [],
        risk_hint_ids: [],
      },
    ],
    edges: [
      {
        id: "edge:agent-flow",
        source_id: null,
        flow_id: "flow:agent",
        from: "component:agent",
        to: "reference:planner",
        relationship: "controls",
        label: null,
        evidence_ids: [],
        risk_hint_ids: [],
      },
    ],
    relationships: [
      {
        id: "relationship:planner-agent",
        kind: "reference_component_mapping",
        source_node_id: "reference:planner",
        target_node_id: "component:agent",
        evidence_ids: ["evidence:planner"],
      },
    ],
    endpoints: [
      {
        endpoint_id: "endpoint:local:api",
        value: "http://127.0.0.1:8000",
        endpoint_type: "local",
        method: "POST",
        component_id: "component:agent",
        slot: null,
      },
    ],
    recommended_next_checks: [
      {
        id: "next-check:runtime",
        target_type: "reference_capability",
        target: "planner",
        reason: "Static evidence cannot prove runtime execution.",
        action: "Run a bounded runtime trace.",
      },
    ],
    details: {
      evidence_by_id: {},
      risk_hints_by_id: {},
      reference_assessments_by_id: {
        planner: { reference_node_id: "planner", status: "conflicted" },
      },
      profile_findings_by_id: {},
      capability_candidates_by_id: {},
    },
    filters: {
      available: [
        {
          id: "filter:reference_capabilities",
          label: "Reference capabilities",
          kind: "semantic_kind",
          active: false,
          matches_node_ids: ["reference:planner"],
          matches_edge_ids: [],
        },
      ],
      lenses: [
        lens("lens:data", "Data"),
        lens("lens:control", "Control"),
        lens("lens:evidence", "Evidence"),
        lens("lens:governance", "Governance"),
        lens("lens:source", "Source"),
        lens("lens:risk", "Risk"),
      ],
      behavior: "highlight",
    },
  };
}

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
      graph_view_model: plan06GraphProjectionFixture(),
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

  it("preserves Plan 06 projection identity when /api/map wraps a v1 canonical artifact", () => {
    const normalized = parseViewerPayload({
      viewer_load_result: {
        loaded: true,
        error_reason: null,
        map_json: "ai_system_map.json",
        ai_system_map: { schema_version: "ai-system-map/v1" },
        graph_view_model: plan06GraphProjectionFixture(),
      },
    });

    expect(normalized.contract_source).toBe("phase2");
    expect(normalized.viewer_load_result.project_id).toBe("project:sample-ai-health-rag");
    expect(normalized.viewer_load_result.scan_id).toBe("scan:sample-s1");
    expect(normalized.viewer_load_result.build_id).toBe("build:sample-b2");
    expect(normalized.viewer_load_result.environment_id).toBe("environment:default-static");
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
    expect(result.graph_view_model.nodes).toHaveLength(2);
    expect(result.graph_view_model.nodes[0].conflict_fields).toEqual([
      { field: "status", reason: "positive and negative evidence disagree" },
    ]);
    expect(result.graph_view_model.nodes[1].component_id).toBe("component:agent");
    expect(result.graph_view_model.relationships).toHaveLength(1);
    expect(result.graph_view_model.endpoints).toHaveLength(1);
    expect(result.graph_view_model.recommended_next_checks).toHaveLength(1);
    expect(result.graph_view_model.details.reference_assessments_by_id.planner).toMatchObject({
      status: "conflicted",
    });
    expect(result.graph_view_model.filters.lenses).toHaveLength(6);
  });

  it("rejects a sidecar from a different build", () => {
    const invalid = mapBuildResponseFixture();
    if (!invalid.build_result.readiness_report) throw new Error("fixture requires a readiness report");
    invalid.build_result.readiness_report.build_id = "build:other";

    expect(() => parseMapBuildPayload(invalid)).toThrow(/readiness_report\.build_id must match/);
  });

  it("rejects a graph projection from a different build", () => {
    const invalid = mapBuildResponseFixture();
    invalid.viewer_load_result.graph_view_model.build_id = "build:other";

    expect(() => parseMapBuildPayload(invalid)).toThrow(/graph_view_model\.build_id must match/);
  });

  it("uses graph projection scope when sidecars are absent", () => {
    const fixture = mapBuildResponseFixture();
    fixture.build_result.profile_inference_result = null;
    fixture.build_result.readiness_report = null;
    fixture.build_result.profile_signals_available = false;
    fixture.build_result.readiness_report_available = false;

    const normalized = parseMapBuildPayload(fixture);
    expect(normalized.viewer_load_result.environment_id).toBe("environment:default-static");
    expect(normalized.viewer_load_result.build_id).toBe("build:sample-b2");
  });
});

describe("extractMappingCompleteness", () => {
  it("prefers the graph projection value and falls back to the profile sidecar", () => {
    const target = parseViewerPayload(phase2ViewerSample);
    expect(extractMappingCompleteness(target)?.denominator).toBe(52);

    const graphScoped = parseMapBuildPayload(mapBuildResponseFixture());
    expect(graphScoped.viewer_load_result.graph_view_model.mapping_completeness?.numerator).toBe(40);
    expect(extractMappingCompleteness(graphScoped)?.numerator).toBe(40);

    const fallbackFixture = mapBuildResponseFixture();
    delete (fallbackFixture.viewer_load_result.graph_view_model as Record<string, unknown>)
      .mapping_completeness;
    expect(extractMappingCompleteness(parseMapBuildPayload(fallbackFixture))?.denominator).toBe(52);
  });

  it("returns undefined instead of fabricating a value", () => {
    const fixture = mapBuildResponseFixture();
    fixture.build_result.profile_inference_result = null;
    delete (fixture.viewer_load_result.graph_view_model as Record<string, unknown>).mapping_completeness;

    expect(extractMappingCompleteness(parseMapBuildPayload(fixture))).toBeUndefined();
  });
});
