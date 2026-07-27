import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createDetailScan,
  detailScanRequest,
  viewerPayloadFromDetailScan,
  type DetailScanTarget,
} from "../services/detailScanApi";
import { ApiRequestError } from "../services/http";
import { loadMapBuildViewerPayload } from "../services/viewerApi";
import type { DetailScanDepth, DetailScanResponse, ViewerPayload } from "../types";

type Scope = {
  apiBaseUrl: string;
  projectId: string | null;
  buildId: string | null;
};

type RunDetailScanOptions = {
  target: DetailScanTarget;
  scanDepth: DetailScanDepth;
};

export type DetailScanRunResult = {
  request: RunDetailScanOptions;
  response: DetailScanResponse;
  childPayload: ViewerPayload;
  hydrationWarning?: string;
};

const STALE_BASE_CODES = new Set(["base_build_not_latest", "scan_snapshot_stale"]);

export function useDetailScan({ apiBaseUrl, projectId, buildId }: Scope) {
  const queryClient = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const requestedBuildIdRef = useRef<string | null>(null);
  const [results, setResults] = useState<DetailScanRunResult[]>([]);
  const scopeRef = useRef({ apiBaseUrl, projectId, buildId });
  scopeRef.current = { apiBaseUrl, projectId, buildId };

  const mutation = useMutation({
    mutationFn: async (request: RunDetailScanOptions): Promise<DetailScanRunResult> => {
      if (!projectId || !buildId) {
        throw new Error("Detail Scan requires the current project and build identity.");
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      requestedBuildIdRef.current = buildId;
      const response = await createDetailScan(
        apiBaseUrl,
        detailScanRequest(projectId, buildId, request.target, request.scanDepth),
        controller.signal,
      );

      if (response.project_id !== projectId || response.source_build_id !== buildId) {
        throw new Error("Detail Scan child lineage does not match the current project/build.");
      }

      const directChildPayload = viewerPayloadFromDetailScan(response);
      try {
        const childPayload = await loadMapBuildViewerPayload(apiBaseUrl, response.build_id as string, controller.signal);
        return { request, response, childPayload };
      } catch (error) {
        if (controller.signal.aborted) throw error;
        return {
          request,
          response,
          childPayload: directChildPayload,
          hydrationWarning:
            error instanceof Error
              ? `Child build was created, but its full build-scoped metadata could not be loaded: ${error.message}`
              : "Child build was created, but its full build-scoped metadata could not be loaded.",
        };
      }
    },
    onSuccess: (result) => {
      const current = scopeRef.current;
      if (
        current.apiBaseUrl !== apiBaseUrl ||
        current.projectId !== result.response.project_id ||
        current.buildId !== result.response.source_build_id
      ) {
        return;
      }
      queryClient.setQueryData(
        ["viewer-load-result", "api", apiBaseUrl, result.response.project_id, null],
        result.childPayload,
      );
      setResults((currentResults) => [
        ...currentResults.filter((item) => item.response.build_id !== result.response.build_id),
        result,
      ]);
      void queryClient.invalidateQueries({ queryKey: ["map-builds", apiBaseUrl, result.response.project_id] });
    },
  });

  useEffect(() => {
    setResults([]);
  }, [apiBaseUrl, projectId]);

  useEffect(() => {
    abortRef.current?.abort();
    return () => abortRef.current?.abort();
    // Cancel strictly when the immutable request scope changes. Successful
    // child data stays available while the viewer switches parent -> child.
  }, [apiBaseUrl, projectId, buildId]);

  const error = mutation.error instanceof Error ? mutation.error : null;
  const errorCode = error?.message;

  return {
    run: mutation.mutate,
    reset: mutation.reset,
    data: mutation.data,
    results,
    variables: mutation.variables,
    requestBuildId: requestedBuildIdRef.current,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: error?.message,
    isStaleBase:
      error instanceof ApiRequestError && error.status === 409 && errorCode != null && STALE_BASE_CODES.has(errorCode),
    refreshCurrentBuild: () =>
      queryClient.invalidateQueries({
        queryKey: ["viewer-load-result", "api", apiBaseUrl, projectId, null],
      }),
  };
}
