import { useCallback, useEffect, useRef, useState } from "react";
import { createQueryTrace, type TraceCreateRequest } from "../services/traceApi";
import type { TraceRunResult } from "../types";

type TraceRequestState = "idle" | "loading" | "success" | "error";

export function useQueryTrace(apiBaseUrl: string) {
  const [state, setState] = useState<TraceRequestState>("idle");
  const [result, setResult] = useState<TraceRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const runTrace = useCallback(
    async (request: TraceCreateRequest) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState("loading");
      setError(null);

      try {
        const response = await createQueryTrace(apiBaseUrl, request, controller.signal);
        setResult(response);
        setState("success");
        return response;
      } catch (caught) {
        if (controller.signal.aborted) {
          setState("idle");
          return null;
        }

        setError(caught instanceof Error ? caught.message : String(caught));
        setState("error");
        return null;
      }
    },
    [apiBaseUrl],
  );

  const resetTrace = useCallback(() => {
    abortRef.current?.abort();
    setState("idle");
    setError(null);
    setResult(null);
  }, []);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return {
    state,
    result,
    error,
    isLoading: state === "loading",
    runTrace,
    resetTrace,
  };
}
