import { traceRunResultSchema, type TraceCreateRequest, type TraceRunResult } from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

const TRACE_NETWORK_BUFFER_MS = 10_000;

export async function createQueryTrace(
  baseUrl: string,
  request: TraceCreateRequest,
  signal?: AbortSignal,
): Promise<TraceRunResult> {
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/trace`, {
    method: "POST",
    signal,
    timeoutMs: request.timeout_seconds * 1_000 + TRACE_NETWORK_BUFFER_MS,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  return traceRunResultSchema.parse(payload);
}
