import { apiErrorSchema, typedApiErrorDetailSchema } from "../types";

export const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

export class ApiRequestError extends Error {
  status?: number;
  code?: string;
  retryable?: boolean;
  context?: Record<string, unknown> | null;

  constructor(
    message: string,
    status?: number,
    detail?: { code: string; retryable: boolean; context?: Record<string, unknown> | null },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = detail?.code;
    this.retryable = detail?.retryable;
    this.context = detail?.context;
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
      const error = await responseError(response);
      throw new ApiRequestError(error.message, response.status, error.detail);
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

async function responseError(response: Response): Promise<{
  message: string;
  detail?: { code: string; retryable: boolean; context?: Record<string, unknown> | null };
}> {
  try {
    const payload = apiErrorSchema.parse(await response.json());
    if (typeof payload.detail === "string") return { message: payload.detail };
    const typedDetail = typedApiErrorDetailSchema.safeParse(payload.detail);
    if (typedDetail.success) {
      return {
        message: typedDetail.data.message,
        detail: {
          code: typedDetail.data.code,
          retryable: typedDetail.data.retryable,
          context: typedDetail.data.context,
        },
      };
    }
  } catch {
    // Fall through to status text when the error body is not JSON.
  }
  return { message: `${response.status} ${response.statusText}` };
}
