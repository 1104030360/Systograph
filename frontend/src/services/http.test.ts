import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, fetchJson, fetchText } from "./http";

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

describe("fetchText", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("returns a successful response as text", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("# AI system map", {
        status: 200,
        headers: { "Content-Type": "text/markdown" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchText("http://127.0.0.1:8000/api/map/report")).resolves.toBe(
      "# AI system map",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/map/report",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("Accept")).toBe("text/plain");
  });

  it("preserves typed API errors for non-success responses", async () => {
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

    await expect(fetchText("http://127.0.0.1:8000/api/map/report")).rejects.toMatchObject({
      name: ApiRequestError.name,
      status: 404,
      message: "map_markdown_not_available",
    });
  });

  it("reports a timeout through the shared request policy", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", pendingFetch());

    const request = fetchText("http://127.0.0.1:8000/api/map/report", { timeoutMs: 1_000 });
    const expectation = expect(request).rejects.toMatchObject({
      name: ApiRequestError.name,
      message: "Request timed out. Check that the local API server is running.",
    });

    await vi.advanceTimersByTimeAsync(1_000);
    await expectation;
  });
});
