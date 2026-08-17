import {
  mapBuildHistoryResponseSchema,
  parseMapBuildPayload,
  type MapBuildHistorySummary,
} from "../contracts/viewer";
import { scanProgressEventSchema, type ScanProgressEvent, type ViewerPayload } from "../types";
import { viewerPayload as sampleViewerPayload } from "../data/sampleMap";
import { fetchJson, normalizeBaseUrl } from "./http";

export async function loadSampleViewerPayload(): Promise<ViewerPayload> {
  return sampleViewerPayload;
}

export async function loadApiViewerPayload(
  baseUrl: string,
  projectId: string,
  signal?: AbortSignal,
): Promise<ViewerPayload> {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const endpoint = `/api/projects/${encodeURIComponent(projectId)}/map-builds/latest`;
  const payload = await fetchJson(`${normalizedBaseUrl}${endpoint}`, { signal });
  return parseMapBuildPayload(payload);
}

export async function listMapBuilds(
  baseUrl: string,
  projectId: string,
  signal?: AbortSignal,
): Promise<MapBuildHistorySummary[]> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/projects/${encodeURIComponent(projectId)}/map-builds`;
  const payload = await fetchJson(url, { signal });
  return mapBuildHistoryResponseSchema.parse(payload).builds;
}

export async function loadMapBuildViewerPayload(
  baseUrl: string,
  buildId: string,
  signal?: AbortSignal,
): Promise<ViewerPayload> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/map-builds/${encodeURIComponent(buildId)}`;
  const payload = await fetchJson(url, { signal });
  return parseMapBuildPayload(payload);
}

export function createScanEventSource(baseUrl: string): EventSource {
  return new EventSource(`${normalizeBaseUrl(baseUrl)}/api/scan/events`);
}

export function parseScanProgressEvent(rawData: string): ScanProgressEvent | null {
  if (!rawData.trim()) return null;

  try {
    return scanProgressEventSchema.parse(JSON.parse(rawData));
  } catch {
    return {
      event: "invalid_event",
      status: "warning",
      message: "Received an unrecognized scan progress event.",
    };
  }
}
