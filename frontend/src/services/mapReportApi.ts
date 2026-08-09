import { ApiRequestError, fetchText, normalizeBaseUrl } from "./http";

const MAP_REPORT_PATH = "/api/map/report";

export class MapReportUnavailableError extends Error {
  constructor() {
    super("The latest scan report is not available yet.");
    this.name = "MapReportUnavailableError";
  }
}

export function mapReportDownloadUrl(baseUrl: string): string {
  return `${normalizeBaseUrl(baseUrl)}${MAP_REPORT_PATH}?download=true`;
}

async function fetchMapReport(url: string, signal?: AbortSignal): Promise<string> {
  try {
    return await fetchText(url, {
      signal,
      headers: { Accept: "text/markdown" },
    });
  } catch (error) {
    if (
      error instanceof ApiRequestError &&
      error.status === 404 &&
      error.message === "map_markdown_not_available"
    ) {
      throw new MapReportUnavailableError();
    }
    throw error;
  }
}

export function loadMapReport(baseUrl: string, signal?: AbortSignal): Promise<string> {
  return fetchMapReport(`${normalizeBaseUrl(baseUrl)}${MAP_REPORT_PATH}`, signal);
}

export async function downloadMapReport(baseUrl: string, signal?: AbortSignal): Promise<Blob> {
  const markdown = await fetchMapReport(mapReportDownloadUrl(baseUrl), signal);
  return new Blob([markdown], { type: "text/markdown;charset=utf-8" });
}
