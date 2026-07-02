import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, fetchJson } from "./http";

function pendingFetch() {
  return vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
    return new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener(
        "abort",
        () => reject(new DOMException("The operation was aborted.", "AbortError")),
        { once: true },
      );
    });
  });
}

describe("fetchJson cancellation", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("reports a timeout when its bounded timer aborts the request", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", pendingFetch());

    const request = fetchJson("http://127.0.0.1:8000/api/map", { timeoutMs: 1_000 });
    const expectation = expect(request).rejects.toMatchObject({
      name: ApiRequestError.name,
      message: "Request timed out. Check that the local API server is running.",
    });

    await vi.advanceTimersByTimeAsync(1_000);
    await expectation;
  });

  it("distinguishes caller cancellation from a timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", pendingFetch());
    const controller = new AbortController();

    const request = fetchJson("http://127.0.0.1:8000/api/map", {
      signal: controller.signal,
      timeoutMs: 15_000,
    });
    const expectation = expect(request).rejects.toMatchObject({
      name: ApiRequestError.name,
      message: "Request was cancelled.",
    });

    controller.abort();
    await expectation;
  });
});
