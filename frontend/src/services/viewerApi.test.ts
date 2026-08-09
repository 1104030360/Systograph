import { beforeEach, describe, expect, it, vi } from "vitest";
import profileInferenceSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-06-derived-assessment/frontend-profile-signals-sample.json";
import readinessReportSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-06-derived-assessment/frontend-readiness-report-sample.json";
import graphViewModelSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-07-projection-publication/frontend-graph-view-model-sample.json";
import canonicalMapSample from "../data/frontend-ai-system-map-v2-canonical.json";
import { fetchJson } from "./http";
import {
  listMapBuilds,
  loadApiViewerPayload,
  loadMapBuildViewerPayload,
} from "./viewerApi";

vi.mock("./http", () => ({
  fetchJson: vi.fn(),
  normalizeBaseUrl: (value: string) => value.replace(/\/$/, ""),
}));

function scopeFixture(value: unknown, buildId: string): unknown {
  if (Array.isArray(value)) return value.map((item) => scopeFixture(item, buildId));
  if (value == null || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      key === "build_id" || key === "generated_from_build_id"
        ? buildId
        : scopeFixture(item, buildId),
    ]),
  );
}

function buildResponse(buildId = "build:sample-b2") {
  return {
    project_id: "project:sample-ai-health-rag",
    scan_id: "scan:sample-s1",
    build_id: buildId,
    based_on_build_id: buildId === "build:sample-b2" ? null : "build:sample-b2",
    build_reason: buildId === "build:sample-b2" ? "initial_scan" : "detail_scan",
    applied_mapping_ids: [],
    build_result: {
      status: "ok",
      project_name: "sample-ai-health-rag",
      active_schema_version: "ai-system-map/v2",
      requested_schema_version: "ai-system-map/v2",
      source_schema_version: "ai-system-map/v2",
      operator_rollback_active: false,
      migration_warnings: [],
      warnings: [],
      profile_signals_available: true,
      readiness_report_available: true,
      profile_inference_result: scopeFixture(profileInferenceSample, buildId),
      readiness_report: scopeFixture(readinessReportSample, buildId),
    },
    viewer_load_result: {
      loaded: true,
      error_reason: null,
      ai_system_map: scopeFixture(canonicalMapSample, buildId),
      graph_view_model: scopeFixture(graphViewModelSample, buildId),
    },
  };
}

describe("viewerApi build identity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the selected project's latest build from the project-scoped endpoint", async () => {
    vi.mocked(fetchJson).mockResolvedValue(buildResponse());

    const payload = await loadApiViewerPayload(
      "http://127.0.0.1:8000/",
      "project:sample-ai-health-rag",
    );

    expect(fetchJson).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/projects/project%3Asample-ai-health-rag/map-builds/latest",
      { signal: undefined },
    );
    expect(payload.viewer_load_result.project_id).toBe("project:sample-ai-health-rag");
    expect(payload.viewer_load_result.build_id).toBe("build:sample-b2");
    expect(payload.viewer_load_result.readiness_report?.build_id).toBe("build:sample-b2");
  });

  it("surfaces a project-scoped load failure without calling a retired fallback", async () => {
    const failure = new Error("Latest build is unavailable.");
    vi.mocked(fetchJson).mockRejectedValue(failure);

    await expect(
      loadApiViewerPayload("http://127.0.0.1:8000", "project:sample-ai-health-rag"),
    ).rejects.toBe(failure);

    expect(fetchJson).toHaveBeenCalledOnce();
    expect(fetchJson).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/projects/project%3Asample-ai-health-rag/map-builds/latest",
      { signal: undefined },
    );
  });

  it("loads the explicitly selected historical build without falling back to latest", async () => {
    vi.mocked(fetchJson).mockResolvedValue(buildResponse("build:historical-b1"));

    const payload = await loadMapBuildViewerPayload(
      "http://127.0.0.1:8000",
      "build:historical-b1",
    );

    expect(fetchJson).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/map-builds/build%3Ahistorical-b1",
      { signal: undefined },
    );
    expect(payload.viewer_load_result.build_id).toBe("build:historical-b1");
    expect(payload.viewer_load_result.profile_inference_result?.build_id).toBe("build:historical-b1");
    expect(payload.viewer_load_result.readiness_report?.build_id).toBe("build:historical-b1");
  });

  it("preserves backend lineage identity in the history list", async () => {
    vi.mocked(fetchJson).mockResolvedValue({
      project_id: "project:sample-ai-health-rag",
      builds: [
        {
          project_id: "project:sample-ai-health-rag",
          scan_id: "scan:sample-s1",
          build_id: "build:sample-b2",
          based_on_build_id: null,
          build_reason: "initial_scan",
          applied_mapping_ids: [],
          generated_at: "2026-07-21T08:00:00Z",
        },
        {
          project_id: "project:sample-ai-health-rag",
          scan_id: "scan:sample-s1",
          build_id: "build:historical-b1",
          based_on_build_id: "build:sample-b2",
          build_reason: "detail_scan",
          applied_mapping_ids: [],
          generated_at: "2026-07-21T09:00:00Z",
        },
      ],
    });

    const builds = await listMapBuilds(
      "http://127.0.0.1:8000",
      "project:sample-ai-health-rag",
    );

    expect(builds.map((build) => build.build_id)).toEqual([
      "build:sample-b2",
      "build:historical-b1",
    ]);
    expect(builds[1].based_on_build_id).toBe("build:sample-b2");
  });
});
