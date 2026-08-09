import { afterEach, describe, expect, it, vi } from "vitest";
import { loadMapReport, mapReportDownloadUrl, MapReportUnavailableError } from "./mapReportApi";

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
});
