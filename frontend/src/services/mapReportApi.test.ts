import { afterEach, describe, expect, it, vi } from "vitest";
import {
  MAP_REPORT_FILE_NAME,
  MapReportError,
  downloadMapBuildReport,
  loadMapBuildReport,
} from "./mapReportApi";

const BASE_URL = "http://127.0.0.1:8000";
const MARKDOWN = "# AI System Map\n\n- Build: `build:b1`\n";

function markdownResponse(body = MARKDOWN) {
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/markdown; charset=utf-8" },
  });
}

function detailResponse(detail: unknown, status = 404) {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function stubObjectUrls(objectUrl = "blob:systograph/ai-system-map") {
  const createObjectURL = vi.fn<(blob: Blob) => string>(() => objectUrl);
  const revokeObjectURL = vi.fn<(url: string) => void>();
  URL.createObjectURL = createObjectURL;
  URL.revokeObjectURL = revokeObjectURL;
  return { createObjectURL, revokeObjectURL, objectUrl };
}

function stubAnchorClick() {
  const clicks: { download: string; href: string; connected: boolean }[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    clicks.push({ download: this.download, href: this.href, connected: this.isConnected });
  });
  return clicks;
}

function flushMacrotasks() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  Reflect.deleteProperty(URL, "createObjectURL");
  Reflect.deleteProperty(URL, "revokeObjectURL");
});

describe("loadMapBuildReport", () => {
  it("reads the build-scoped artifact with an encoded build id", async () => {
    const fetchMock = stubFetch(markdownResponse());

    await expect(loadMapBuildReport(BASE_URL, "build:b1")).resolves.toBe(MARKDOWN);

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "http://127.0.0.1:8000/api/map-builds/build%3Ab1/artifacts/ai_system_map.md",
    );
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("Accept")).toBe("text/markdown");
  });

  it("never asks for the attachment variant because it saves the bytes itself", async () => {
    const fetchMock = stubFetch(markdownResponse());

    await loadMapBuildReport(BASE_URL, "build:b1");

    expect(String(fetchMock.mock.calls[0][0])).not.toContain("download");
  });

  it.each([
    ["build_not_found"],
    ["artifact_not_available"],
    ["artifact_not_found"],
  ])("classifies the %s 404", async (detail) => {
    stubFetch(detailResponse(detail));

    await expect(loadMapBuildReport(BASE_URL, "build:b1")).rejects.toMatchObject({
      name: "MapReportError",
      reason: detail,
      status: 404,
    });
  });

  it("treats an undocumented 404 as unknown", async () => {
    stubFetch(detailResponse("Not Found"));

    await expect(loadMapBuildReport(BASE_URL, "build:b1")).rejects.toMatchObject({
      name: "MapReportError",
      reason: "unknown",
      status: 404,
    });
  });

  it("treats the 422 array-detail form as unknown", async () => {
    stubFetch(detailResponse([{ loc: ["query", "download"], msg: "bool parsing failed" }], 422));

    await expect(loadMapBuildReport(BASE_URL, "build:b1")).rejects.toMatchObject({
      name: "MapReportError",
      reason: "unknown",
      status: 422,
    });
  });

  it("wraps transport failures as unknown MapReportError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await loadMapBuildReport(BASE_URL, "build:b1").catch((caught) => caught);
    expect(error).toBeInstanceOf(MapReportError);
    expect(error.reason).toBe("unknown");
  });
});

describe("downloadMapBuildReport", () => {
  it("downloads through a connected anchor and delays object URL revocation", async () => {
    stubFetch(markdownResponse());
    const { createObjectURL, revokeObjectURL, objectUrl } = stubObjectUrls();
    const clicks = stubAnchorClick();

    await downloadMapBuildReport(BASE_URL, "build:b1");

    expect(revokeObjectURL).not.toHaveBeenCalled();
    expect(createObjectURL).toHaveBeenCalledOnce();
    const blob = createObjectURL.mock.calls[0][0];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe("text/markdown");
    await expect(blob.text()).resolves.toBe(MARKDOWN);
    expect(clicks).toEqual([{ download: MAP_REPORT_FILE_NAME, href: objectUrl, connected: true }]);
    expect(document.querySelector("a[download]")).toBeNull();

    await flushMacrotasks();
    expect(revokeObjectURL).toHaveBeenCalledWith(objectUrl);
  });

  it("does not create a download when the artifact is unavailable", async () => {
    stubFetch(detailResponse("artifact_not_available"));
    const { createObjectURL } = stubObjectUrls();
    const clicks = stubAnchorClick();

    await expect(downloadMapBuildReport(BASE_URL, "build:b1")).rejects.toMatchObject({
      name: "MapReportError",
      reason: "artifact_not_available",
    });
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(clicks).toEqual([]);
  });
});
