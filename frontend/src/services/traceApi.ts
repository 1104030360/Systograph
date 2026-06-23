import { traceRunResultSchema, type TraceRunResult } from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type TraceCreateRequest = {
  project_id: string;
  endpoint_id: string;
  query: string;
  timeout_seconds: number;
};

export async function createQueryTrace(
  baseUrl: string,
  request: TraceCreateRequest,
  signal?: AbortSignal,
): Promise<TraceRunResult> {
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/trace`, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  return traceRunResultSchema.parse(payload);
}
