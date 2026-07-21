import canonicalMapSample from "./frontend-ai-system-map-v2-canonical.json";
import profileInferenceSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-06-derived-assessment/frontend-profile-signals-sample.json";
import readinessReportSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-06-derived-assessment/frontend-readiness-report-sample.json";
import graphViewModelSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-07-projection-publication/frontend-graph-view-model-sample.json";
import { parseViewerPayload } from "../contracts/viewer";
import { traceEventSchema, type TraceEvent, type ViewerPayload } from "../types";

const SAMPLE_BUILD_ID = canonicalMapSample.build_id;

function scopeHandoffFixtureToBuild(value: unknown, buildId: string): unknown {
  if (Array.isArray(value)) return value.map((item) => scopeHandoffFixtureToBuild(item, buildId));
  if (value == null || typeof value !== "object") return value;

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      key === "build_id" || key === "generated_from_build_id"
        ? buildId
        : scopeHandoffFixtureToBuild(item, buildId),
    ]),
  );
}

/* Active Sample mode is a real v2 envelope composed from Timmy's Step 4, 6,
   and 7 handoff fixtures. Step 6 was published for b1, so the frontend sample
   adapter re-scopes every nested build identity to the Step 4/7 b2 sample. */
export const viewerPayload: ViewerPayload = parseViewerPayload({
  loaded: true,
  error_reason: null,
  warnings: [],
  project_id: canonicalMapSample.project.project_id,
  scan_id: canonicalMapSample.scan_id,
  build_id: SAMPLE_BUILD_ID,
  environment_id: canonicalMapSample.environment_id,
  generated_from_build_id: SAMPLE_BUILD_ID,
  based_on_build_id: "build:sample-b1",
  applied_mapping_ids: ["mapping:reranker-review"],
  artifact_refs: [],
  map_json: null,
  ai_system_map: canonicalMapSample,
  profile_inference_result: scopeHandoffFixtureToBuild(profileInferenceSample, SAMPLE_BUILD_ID),
  readiness_report: scopeHandoffFixtureToBuild(readinessReportSample, SAMPLE_BUILD_ID),
  graph_view_model: graphViewModelSample,
});

export const graphViewModel = viewerPayload.viewer_load_result.graph_view_model;

export const aiSystemMap = viewerPayload.viewer_load_result.ai_system_map;

function parseTraceEvents(raw: unknown): TraceEvent[] {
  if (!Array.isArray(raw)) return [];

  return raw
    .flatMap((item) => {
      const parsed = traceEventSchema.safeParse(item);
      return parsed.success ? [parsed.data] : [];
    })
    .sort((a, b) => (a.sequence_index ?? 0) - (b.sequence_index ?? 0));
}

export function getTraceEvents(payload: ViewerPayload): TraceEvent[] {
  return parseTraceEvents(payload.viewer_load_result.ai_system_map.query_trace_events);
}

export const defaultTraceEvents: TraceEvent[] = getTraceEvents(viewerPayload);

export const timeoutTraceEvents: TraceEvent[] = parseTraceEvents(
  viewerPayload.trace_result_samples?.timeout_partial_replay?.events,
);
