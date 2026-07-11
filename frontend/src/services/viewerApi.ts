import { parseMapBuildPayload, parseViewerPayload } from "../contracts/viewer";
import { scanProgressEventSchema, type ScanProgressEvent, type ViewerPayload } from "../types";
import { viewerPayload as sampleViewerPayload } from "../data/sampleMap";
import { fetchJson, normalizeBaseUrl } from "./http";

const mapEndpoints = ["/api/map", "/map"];

export async function loadSampleViewerPayload(): Promise<ViewerPayload> {
  return sampleViewerPayload;
}

export async function loadApiViewerPayload(
  baseUrl: string,
  signal?: AbortSignal,
  projectId?: string | null,
): Promise<ViewerPayload> {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const errors: string[] = [];

  // Build-scoped latest is the primary API-mode read (API-GUIDE §map-builds);
  // the process-wide /api/map endpoints stay as demo/legacy fallback.
  if (projectId) {
    const endpoint = `/api/projects/${encodeURIComponent(projectId)}/map-builds/latest`;
    try {
      const payload = await fetchJson(`${normalizedBaseUrl}${endpoint}`, { signal });
      return parseMapBuildPayload(payload);
    } catch (error) {
      errors.push(`${endpoint}: ${error instanceof Error ? error.message : String(error)}`);
      if (signal?.aborted) {
        throw new Error(`Unable to load viewer payload from ${normalizedBaseUrl}. Tried ${errors.join("; ")}`);
      }
    }
  }

  for (const endpoint of mapEndpoints) {
    const url = `${normalizedBaseUrl}${endpoint}`;

    try {
      const payload = await fetchJson(url, { signal });
      return parseViewerPayload(payload);
    } catch (error) {
      errors.push(`${endpoint}: ${error instanceof Error ? error.message : String(error)}`);
      // A cancelled request must not fall through to the next endpoint.
      if (signal?.aborted) break;
    }
  }

  throw new Error(`Unable to load viewer payload from ${normalizedBaseUrl}. Tried ${errors.join("; ")}`);
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
