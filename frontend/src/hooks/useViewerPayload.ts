import { useQuery } from "@tanstack/react-query";
import type { DataSourceMode } from "../types";
import { loadApiViewerPayload, loadSampleViewerPayload } from "../services/viewerApi";

export function useViewerPayload(mode: DataSourceMode, apiBaseUrl: string) {
  return useQuery({
    queryKey: ["viewer-load-result", mode, apiBaseUrl],
    queryFn: () => (mode === "api" ? loadApiViewerPayload(apiBaseUrl) : loadSampleViewerPayload()),
    retry: false,
    staleTime: mode === "sample" ? Number.POSITIVE_INFINITY : 5_000,
  });
}
