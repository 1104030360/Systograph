import rawSample from "../../../docs/work/Timmy/design/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/design/frontend-json-sample.json";
import { viewerPayloadSchema, type TraceEvent, type ViewerPayload } from "../types";

export const viewerPayload: ViewerPayload = viewerPayloadSchema.parse(rawSample);

export const graphViewModel = viewerPayload.viewer_load_result.graph_view_model;

export const aiSystemMap = viewerPayload.viewer_load_result.ai_system_map;

export function getTraceEvents(payload: ViewerPayload): TraceEvent[] {
  return [...((payload.viewer_load_result.ai_system_map.query_trace_events as TraceEvent[] | undefined) ?? [])].sort(
    (a, b) => (a.sequence_index ?? 0) - (b.sequence_index ?? 0),
  );
}

export const defaultTraceEvents: TraceEvent[] = getTraceEvents(viewerPayload);

export const timeoutTraceEvents: TraceEvent[] = [
  ...((viewerPayload.trace_result_samples?.timeout_partial_replay?.events as TraceEvent[] | undefined) ?? []),
].sort((a, b) => (a.sequence_index ?? 0) - (b.sequence_index ?? 0));
