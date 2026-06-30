import {
  viewerLoadMapRequestSchema,
  viewerPayloadSchema,
  type ViewerPayload,
} from "../types";
import { fetchJson, fetchText, normalizeBaseUrl } from "./http";

export async function loadExistingViewerMap(
  baseUrl: string,
  mapJsonPath: string,
): Promise<ViewerPayload> {
  const request = viewerLoadMapRequestSchema.parse({
    map_json_path: mapJsonPath,
  });
  const payload = viewerPayloadSchema.parse(
    await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/viewer/load`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
  );

  if (!payload.viewer_load_result.loaded) {
    throw new Error(
      payload.viewer_load_result.error_reason ??
        "The backend could not load this map.",
    );
  }
  return payload;
}

export async function loadLatestMapReport(baseUrl: string): Promise<string> {
  return fetchText(`${normalizeBaseUrl(baseUrl)}/api/map/report`, {
    headers: { Accept: "text/markdown" },
  });
}

export function mapReportDownloadUrl(baseUrl: string): string {
  return `${normalizeBaseUrl(baseUrl)}/api/map/report?download=true`;
}
