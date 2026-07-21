import { useCallback, useEffect, useRef, useState } from "react";
import { createQueryTrace } from "../services/traceApi";
import type { TraceRunResult } from "../types";

export type TraceRequestState = "idle" | "loading" | "success" | "error" | "timeout";

type RunTraceInput = {
  endpointId: string;
  query: string;
  timeoutSeconds: number;
};

function isTimeoutError(error: unknown): boolean {
  return error instanceof Error && error.message.toLocaleLowerCase().includes("timed out");
}

export function useQueryTrace(
  apiBaseUrl: string,
  projectId: string | null,
  buildId: string | null,
) {
  const [state, setState] = useState<TraceRequestState>("idle");
  const [result, setResult] = useState<TraceRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const reset = useCallback(() => {
    requestIdRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    setState("idle");
    setResult(null);
    setError(null);
  }, []);

  useEffect(() => reset(), [apiBaseUrl, buildId, projectId, reset]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const runTrace = useCallback(
    async ({ endpointId, query, timeoutSeconds }: RunTraceInput) => {
      if (!projectId || !buildId) return null;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      setState("loading");
      setError(null);

      try {
        const response = await createQueryTrace(
          apiBaseUrl,
          {
            project_id: projectId,
            build_id: buildId,
            endpoint_id: endpointId,
            query,
            timeout_seconds: timeoutSeconds,
          },
          controller.signal,
        );
        if (requestIdRef.current !== requestId) return null;
        if (response.source_build_id !== buildId) {
          throw new Error("Backend did not bind this result to the selected build.");
        }
        setResult(response);
        setState("success");
        return response;
      } catch (caught) {
        if (requestIdRef.current !== requestId || controller.signal.aborted) return null;
        setError(caught instanceof Error ? caught.message : String(caught));
        setState(isTimeoutError(caught) ? "timeout" : "error");
        return null;
      }
    },
    [apiBaseUrl, buildId, projectId],
  );

  return {
    state,
    result,
    error,
    isLoading: state === "loading",
    runTrace,
    reset,
  };
}
