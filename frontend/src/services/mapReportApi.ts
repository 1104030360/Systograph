import { ApiRequestError, fetchText, normalizeBaseUrl } from "./http";

export const MAP_REPORT_FILE_NAME = "ai_system_map.md";
const MAP_REPORT_MEDIA_TYPE = "text/markdown";

export type MapReportErrorReason =
  | "build_not_found"
  | "artifact_not_available"
  | "artifact_not_found"
  | "unknown";

const CONTRACT_REASONS: MapReportErrorReason[] = [
  "artifact_not_found",
  "build_not_found",
  "artifact_not_available",
];

export class MapReportError extends Error {
  reason: MapReportErrorReason;
  status?: number;

  constructor(reason: MapReportErrorReason, message: string, status?: number) {
    super(message);
    this.name = "MapReportError";
    this.reason = reason;
    this.status = status;
  }
}

export async function loadMapBuildReport(
  baseUrl: string,
  buildId: string,
  signal?: AbortSignal,
): Promise<string> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/map-builds/${encodeURIComponent(buildId)}/artifacts/${MAP_REPORT_FILE_NAME}`;

  try {
    return await fetchText(url, {
      signal,
      headers: { Accept: MAP_REPORT_MEDIA_TYPE },
    });
  } catch (error) {
    throw asMapReportError(error);
  }
}

export async function downloadMapBuildReport(
  baseUrl: string,
  buildId: string,
  signal?: AbortSignal,
): Promise<void> {
  const markdown = await loadMapBuildReport(baseUrl, buildId, signal);
  const objectUrl = URL.createObjectURL(new Blob([markdown], { type: MAP_REPORT_MEDIA_TYPE }));
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = MAP_REPORT_FILE_NAME;
  document.body.append(anchor);

  try {
    anchor.click();
  } finally {
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  }
}

function asMapReportError(error: unknown): MapReportError {
  if (error instanceof MapReportError) return error;
  if (error instanceof ApiRequestError) {
    const reason = CONTRACT_REASONS.find(
      (candidate) => error.status === 404 && error.message === candidate,
    );
    return new MapReportError(reason ?? "unknown", error.message, error.status);
  }
  return new MapReportError("unknown", error instanceof Error ? error.message : String(error));
}
