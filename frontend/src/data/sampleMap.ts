import rawSample from "./frontend-json-sample.json";
import { parseViewerPayload } from "../contracts/viewer";
import { traceEventSchema, type TraceEvent, type ViewerPayload } from "../types";

export const viewerPayload: ViewerPayload = parseViewerPayload(rawSample);

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
