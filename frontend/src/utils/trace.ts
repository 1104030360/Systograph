import { systemEndpointSchema, type SystemEndpoint, type TraceEvent } from "../types";

export function sortTraceEvents(events: TraceEvent[]): TraceEvent[] {
  return [...events].sort((a, b) => {
    const sequenceDelta = (a.sequence_index ?? Number.MAX_SAFE_INTEGER) - (b.sequence_index ?? Number.MAX_SAFE_INTEGER);
    if (sequenceDelta !== 0) return sequenceDelta;
    return (a.id ?? "").localeCompare(b.id ?? "");
  });
}

export function parseSystemEndpoints(raw: unknown): SystemEndpoint[] {
  if (!Array.isArray(raw)) return [];

  return raw.flatMap((item) => {
    const parsed = systemEndpointSchema.safeParse(item);
    return parsed.success ? [parsed.data] : [];
  });
}

export function resolveProjectId(rawMap: unknown): string {
  if (!rawMap || typeof rawMap !== "object") return "";

  const mapRecord = rawMap as Record<string, unknown>;
  const direct = mapRecord.project_id;
  if (typeof direct === "string") return direct;

  const project = mapRecord.project;
  if (!project || typeof project !== "object") return "";

  const projectRecord = project as Record<string, unknown>;
  const projectId = projectRecord.project_id ?? projectRecord.id;
  return typeof projectId === "string" ? projectId : "";
}

export function traceEventHasFailure(event: TraceEvent | undefined): boolean {
  if (!event) return false;
  const status = event.status?.toLowerCase();
  return Boolean(event.error) || status === "failed" || status === "error" || status === "timeout" || status === "blocked";
}

export function traceErrorLabel(error: TraceEvent["error"]): string {
  if (!error) return "ok";
  if (typeof error === "string") return error;
  const code = "code" in error && typeof error.code === "string" ? error.code : undefined;
  return code ?? "error";
}
