import { apiErrorSchema } from "../types";

export const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

export class ApiRequestError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/+$/, "");
}

export async function fetchJson(
  url: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<unknown> {
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, signal, headers, ...requestOptions } = options;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has("Accept")) requestHeaders.set("Accept", "application/json");

  if (signal) {
    if (signal.aborted) controller.abort();
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const response = await fetch(url, {
      ...requestOptions,
      signal: controller.signal,
      headers: requestHeaders,
    });

    if (!response.ok) {
      throw new ApiRequestError(await errorMessage(response), response.status);
    }

    return response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      // The caller's signal aborting means cancellation (unmount, newer
      // request); only our own timer means the request actually timed out.
      if (signal?.aborted) {
        throw new ApiRequestError("Request was cancelled.");
      }
      throw new ApiRequestError("Request timed out. Check that the local API server is running.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function errorMessage(response: Response) {
  try {
    const payload = apiErrorSchema.parse(await response.json());
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // Fall through to status text when the error body is not JSON.
  }
  return `${response.status} ${response.statusText}`;
}
