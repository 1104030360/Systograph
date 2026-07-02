import { traceRunResultSchema, type TraceRunResult } from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type TraceCreateRequest = {
  project_id: string;
  endpoint_id: string;
  query: string;
  timeout_seconds: number;
};

// The HTTP request must outlive the backend trace budget, otherwise the client
// aborts at the default fetch timeout while the trace is still running.
const TRACE_NETWORK_BUFFER_MS = 10_000;

export async function createQueryTrace(
  baseUrl: string,
  request: TraceCreateRequest,
  signal?: AbortSignal,
): Promise<TraceRunResult> {
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/trace`, {
    method: "POST",
    signal,
    timeoutMs: request.timeout_seconds * 1000 + TRACE_NETWORK_BUFFER_MS,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  return traceRunResultSchema.parse(payload);
}
