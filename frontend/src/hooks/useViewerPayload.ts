import { useQuery } from "@tanstack/react-query";
import type { DataSourceMode } from "../types";
import { loadApiViewerPayload, loadMapBuildViewerPayload, loadSampleViewerPayload } from "../services/viewerApi";

export function useViewerPayload(
  mode: DataSourceMode,
  apiBaseUrl: string,
  projectId: string | null = null,
  buildId: string | null = null,
) {
  return useQuery({
    // React Query aborts this signal when the query key changes or the last
    // consumer unmounts, so a stale request cannot outlive its consumer.
    queryKey: ["viewer-load-result", mode, apiBaseUrl, projectId, buildId],
    queryFn: ({ signal }) => {
      if (mode !== "api") return loadSampleViewerPayload();
      // A pinned historical build is immutable, so it loads by id. Otherwise
      // API mode follows the explicitly selected project's latest build.
      if (buildId) return loadMapBuildViewerPayload(apiBaseUrl, buildId, signal);
      if (!projectId) throw new Error("Select or import a project before loading its map.");
      return loadApiViewerPayload(apiBaseUrl, projectId, signal);
    },
    enabled: mode !== "api" || projectId != null || buildId != null,
    retry: false,
    staleTime: mode === "sample" ? Number.POSITIVE_INFINITY : 5_000,
  });
}
