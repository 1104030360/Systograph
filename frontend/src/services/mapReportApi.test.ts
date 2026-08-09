import { afterEach, describe, expect, it, vi } from "vitest";
import * as mapReportApi from "./mapReportApi";

const { loadMapReport, mapReportDownloadUrl, MapReportUnavailableError } = mapReportApi;

describe("map report API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the process-wide latest Markdown report", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("# AI system map", {
        status: 200,
        headers: { "Content-Type": "text/markdown; charset=utf-8" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadMapReport("http://127.0.0.1:8000/")).resolves.toBe("# AI system map");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/map/report",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("Accept")).toBe("text/markdown");
  });

  it("maps the backend's missing-report response to an explicit state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "map_markdown_not_available" }), {
          status: 404,
          statusText: "Not Found",
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(loadMapReport("http://127.0.0.1:8000")).rejects.toBeInstanceOf(
      MapReportUnavailableError,
    );
  });

  it("builds the fixed download endpoint without accepting an artifact path", () => {
    expect(mapReportDownloadUrl("http://127.0.0.1:8000/")).toBe(
      "http://127.0.0.1:8000/api/map/report?download=true",
    );
  });

  it("downloads Markdown through the shared HTTP policy instead of browser navigation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("# Downloaded AI system map", {
        status: 200,
        headers: { "Content-Type": "text/markdown; charset=utf-8" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const downloadMapReport = (
      mapReportApi as typeof mapReportApi & {
        downloadMapReport: (baseUrl: string, signal?: AbortSignal) => Promise<Blob>;
      }
    ).downloadMapReport;

    const result = await downloadMapReport("http://127.0.0.1:8000/");

    expect(await result.text()).toBe("# Downloaded AI system map");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/map/report?download=true",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("maps a missing report during download to the same explicit state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "map_markdown_not_available" }), {
          status: 404,
          statusText: "Not Found",
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(mapReportApi.downloadMapReport("http://127.0.0.1:8000")).rejects.toBeInstanceOf(
      MapReportUnavailableError,
    );
  });
});
