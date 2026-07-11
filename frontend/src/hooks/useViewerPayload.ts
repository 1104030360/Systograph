import { useQuery } from "@tanstack/react-query";
import type { DataSourceMode } from "../types";
import { loadApiViewerPayload, loadSampleViewerPayload } from "../services/viewerApi";

export function useViewerPayload(mode: DataSourceMode, apiBaseUrl: string, projectId: string | null = null) {
  return useQuery({
    // React Query aborts this signal when the query key changes or the last
    // consumer unmounts, so a stale request cannot outlive its consumer.
    queryKey: ["viewer-load-result", mode, apiBaseUrl, projectId],
    queryFn: ({ signal }) =>
      mode === "api" ? loadApiViewerPayload(apiBaseUrl, signal, projectId) : loadSampleViewerPayload(),
    retry: false,
    staleTime: mode === "sample" ? Number.POSITIVE_INFINITY : 5_000,
  });
}
