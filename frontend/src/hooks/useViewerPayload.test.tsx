import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { viewerPayload as sampleViewerPayload } from "../data/sampleMap";
import {
  loadApiViewerPayload,
  loadMapBuildViewerPayload,
  loadSampleViewerPayload,
} from "../services/viewerApi";
import { useViewerPayload } from "./useViewerPayload";

vi.mock("../services/viewerApi", () => ({
  loadApiViewerPayload: vi.fn(),
  loadMapBuildViewerPayload: vi.fn(),
  loadSampleViewerPayload: vi.fn(),
}));

function setupHook(
  mode: "api" | "sample",
  projectId: string | null = null,
  buildId: string | null = null,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return renderHook(
    () => useViewerPayload(mode, "http://api", projectId, buildId),
    { wrapper },
  );
}

describe("useViewerPayload API scope", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadSampleViewerPayload).mockResolvedValue(sampleViewerPayload);
    vi.mocked(loadApiViewerPayload).mockResolvedValue(sampleViewerPayload);
    vi.mocked(loadMapBuildViewerPayload).mockResolvedValue(sampleViewerPayload);
  });

  it("stays idle and sends no request before a project or build is selected", async () => {
    const { result } = setupHook("api");

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(loadApiViewerPayload).not.toHaveBeenCalled();
    expect(loadMapBuildViewerPayload).not.toHaveBeenCalled();
    expect(loadSampleViewerPayload).not.toHaveBeenCalled();
  });

  it("loads the selected project's latest build without a process-wide fallback", async () => {
    setupHook("api", "project:p1");

    await waitFor(() => expect(loadApiViewerPayload).toHaveBeenCalledOnce());
    expect(loadApiViewerPayload).toHaveBeenCalledWith(
      "http://api",
      "project:p1",
      expect.any(AbortSignal),
    );
    expect(loadMapBuildViewerPayload).not.toHaveBeenCalled();
  });

  it("loads a pinned build directly", async () => {
    setupHook("api", "project:p1", "build:b1");

    await waitFor(() => expect(loadMapBuildViewerPayload).toHaveBeenCalledOnce());
    expect(loadMapBuildViewerPayload).toHaveBeenCalledWith(
      "http://api",
      "build:b1",
      expect.any(AbortSignal),
    );
    expect(loadApiViewerPayload).not.toHaveBeenCalled();
  });

  it("keeps sample mode available as an explicit user choice", async () => {
    setupHook("sample");

    await waitFor(() => expect(loadSampleViewerPayload).toHaveBeenCalledOnce());
    expect(loadApiViewerPayload).not.toHaveBeenCalled();
    expect(loadMapBuildViewerPayload).not.toHaveBeenCalled();
  });
});
