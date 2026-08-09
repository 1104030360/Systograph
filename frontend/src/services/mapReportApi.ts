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

export async function loadMapReport(baseUrl: string, signal?: AbortSignal): Promise<string> {
  try {
    return await fetchText(`${normalizeBaseUrl(baseUrl)}${MAP_REPORT_PATH}`, {
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
