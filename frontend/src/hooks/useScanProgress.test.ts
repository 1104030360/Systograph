import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createScanEventSource, parseScanProgressEvent } from "../services/viewerApi";
import { useScanProgress } from "./useScanProgress";

vi.mock("../services/viewerApi", () => ({
  createScanEventSource: vi.fn(),
  parseScanProgressEvent: vi.fn((rawData: string) => ({ event: "progress", message: rawData })),
}));

type FakeEventSource = {
  readyState: number;
  onmessage: ((event: MessageEvent<string>) => void) | null;
  onerror: ((event: Event) => void) | null;
  addEventListener: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
};

function makeEventSource(): FakeEventSource {
  return {
    readyState: 0,
    onmessage: null,
    onerror: null,
    addEventListener: vi.fn(),
    close: vi.fn(),
  };
}

describe("useScanProgress", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", { CLOSED: 2 });
  });

  it("lets EventSource reconnect after transient errors and degrades after three consecutive failures", () => {
    const source = makeEventSource();
    vi.mocked(createScanEventSource).mockReturnValue(source as unknown as EventSource);
    const onError = vi.fn();

    renderHook(() =>
      useScanProgress({
        mode: "api",
        apiBaseUrl: "http://127.0.0.1:8000",
        enabled: true,
        onEvent: vi.fn(),
        onError,
      }),
    );

    act(() => source.onerror?.(new Event("error")));
    act(() => source.onerror?.(new Event("error")));
    expect(onError).not.toHaveBeenCalled();
    expect(source.close).not.toHaveBeenCalled();

    act(() => source.onerror?.(new Event("error")));
    expect(onError).toHaveBeenCalledWith(
      "SSE connection failed. Using mock progress until backend is available.",
    );
    expect(source.close).toHaveBeenCalledOnce();
  });

  it("resets the consecutive error count after a successful message", () => {
    const source = makeEventSource();
    vi.mocked(createScanEventSource).mockReturnValue(source as unknown as EventSource);
    const onError = vi.fn();
    const onEvent = vi.fn();

    renderHook(() =>
      useScanProgress({
        mode: "api",
        apiBaseUrl: "http://127.0.0.1:8000",
        enabled: true,
        onEvent,
        onError,
      }),
    );

    act(() => source.onerror?.(new Event("error")));
    act(() => source.onerror?.(new Event("error")));
    act(() => source.onmessage?.(new MessageEvent("message", { data: "connected" })));
    act(() => source.onerror?.(new Event("error")));
    act(() => source.onerror?.(new Event("error")));

    expect(parseScanProgressEvent).toHaveBeenCalledWith("connected");
    expect(onEvent).toHaveBeenCalledWith({ event: "progress", message: "connected" });
    expect(onError).not.toHaveBeenCalled();

    act(() => source.onerror?.(new Event("error")));
    expect(onError).toHaveBeenCalledOnce();
  });

  it("degrades immediately when the browser closes the EventSource", () => {
    const source = makeEventSource();
    source.readyState = 2;
    vi.mocked(createScanEventSource).mockReturnValue(source as unknown as EventSource);
    const onError = vi.fn();

    renderHook(() =>
      useScanProgress({
        mode: "api",
        apiBaseUrl: "http://127.0.0.1:8000",
        enabled: true,
        onEvent: vi.fn(),
        onError,
      }),
    );

    act(() => source.onerror?.(new Event("error")));
    expect(onError).toHaveBeenCalledOnce();
    expect(source.close).toHaveBeenCalledOnce();
  });
});
