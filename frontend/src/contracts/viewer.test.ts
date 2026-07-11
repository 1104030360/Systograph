import { describe, expect, it } from "vitest";
import phase2ViewerSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-08-viewer/frontend-json-sample.json";
import legacyViewerSample from "../data/frontend-json-sample.json";
import { parseViewerPayload, phase2ViewerLoadResultSchema } from "./viewer";

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
    expect(parsed.readiness_report?.release_verdict).toBe("needs_review");
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
