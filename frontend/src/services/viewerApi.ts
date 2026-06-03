import { scanProgressEventSchema, viewerPayloadSchema, type ScanProgressEvent, type ViewerPayload } from "../types";
import { viewerPayload as sampleViewerPayload } from "../data/sampleMap";

const mapEndpoints = ["/api/map", "/map"];

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/+$/, "");
}

async function fetchJson(url: string) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function loadSampleViewerPayload(): Promise<ViewerPayload> {
  return sampleViewerPayload;
}

export async function loadApiViewerPayload(baseUrl: string): Promise<ViewerPayload> {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const errors: string[] = [];

  for (const endpoint of mapEndpoints) {
    const url = `${normalizedBaseUrl}${endpoint}`;

    try {
      const payload = await fetchJson(url);
      return viewerPayloadSchema.parse(payload);
    } catch (error) {
      errors.push(`${endpoint}: ${error instanceof Error ? error.message : String(error)}`);
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
