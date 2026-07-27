import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError } from "../services/http";
import type { DetailScanResponse, ViewerPayload } from "../types";
import { useDetailScan } from "./useDetailScan";

const mocks = vi.hoisted(() => ({
  createDetailScan: vi.fn(),
  detailScanRequest: vi.fn((projectId, buildId, target, scanDepth) => ({
    project_id: projectId,
    build_id: buildId,
    target_type: target.targetType,
    target: target.target,
    scan_depth: scanDepth,
  })),
  viewerPayloadFromDetailScan: vi.fn(),
  loadMapBuildViewerPayload: vi.fn(),
}));

vi.mock("../services/detailScanApi", () => ({
  createDetailScan: mocks.createDetailScan,
  detailScanRequest: mocks.detailScanRequest,
  viewerPayloadFromDetailScan: mocks.viewerPayloadFromDetailScan,
}));
vi.mock("../services/viewerApi", () => ({ loadMapBuildViewerPayload: mocks.loadMapBuildViewerPayload }));

const target = { targetType: "component_instance" as const, target: "component:router", label: "Router" };
const response = {
  project_id: "project:p1",
  source_build_id: "build:base",
  build_id: "build:child",
  scan_id: "scan:s1",
  detail_scan: { target: target.target },
} as DetailScanResponse;
const directPayload = { viewer_load_result: { build_id: "build:child" } } as ViewerPayload;
const scopedPayload = { viewer_load_result: { build_id: "build:child", readiness_report: {} } } as ViewerPayload;

describe("useDetailScan", () => {
  let queryClient: QueryClient;
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    vi.clearAllMocks();
    mocks.createDetailScan.mockResolvedValue(response);
    mocks.viewerPayloadFromDetailScan.mockReturnValue(directPayload);
    mocks.loadMapBuildViewerPayload.mockResolvedValue(scopedPayload);
  });

  it("hydrates the exact child build and updates the current project cache", async () => {
    const { result } = renderHook(
      () => useDetailScan({ apiBaseUrl: "http://api", projectId: "project:p1", buildId: "build:base" }),
      { wrapper },
    );

    act(() => result.current.run({ target, scanDepth: "component" }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mocks.detailScanRequest).toHaveBeenCalledWith("project:p1", "build:base", target, "component");
    expect(mocks.loadMapBuildViewerPayload).toHaveBeenCalledWith("http://api", "build:child", expect.any(AbortSignal));
    expect(queryClient.getQueryData(["viewer-load-result", "api", "http://api", "project:p1", null])).toBe(scopedPayload);
  });

  it("keeps the POST child projection as a partial result when hydration fails", async () => {
    mocks.loadMapBuildViewerPayload.mockRejectedValue(new Error("offline"));
    const { result } = renderHook(
      () => useDetailScan({ apiBaseUrl: "http://api", projectId: "project:p1", buildId: "build:base" }),
      { wrapper },
    );

    act(() => result.current.run({ target, scanDepth: "component" }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.hydrationWarning).toMatch(/full build-scoped metadata/);
    expect(queryClient.getQueryData(["viewer-load-result", "api", "http://api", "project:p1", null])).toBe(directPayload);
  });

  it("classifies stale-base conflicts without automatic retry", async () => {
    mocks.createDetailScan.mockRejectedValue(new ApiRequestError("base_build_not_latest", 409));
    const { result } = renderHook(
      () => useDetailScan({ apiBaseUrl: "http://api", projectId: "project:p1", buildId: "build:base" }),
      { wrapper },
    );

    act(() => result.current.run({ target, scanDepth: "component" }));
    await waitFor(() => expect(result.current.isStaleBase).toBe(true));
    expect(mocks.createDetailScan).toHaveBeenCalledOnce();
  });
});
