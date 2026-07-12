import { useQuery } from "@tanstack/react-query";
import type { DataSourceMode } from "../types";
import { listMapBuilds } from "../services/viewerApi";

/** Immutable build history for the imported project (API mode only). */
export function useMapBuilds(mode: DataSourceMode, apiBaseUrl: string, projectId: string | null) {
  return useQuery({
    queryKey: ["map-builds", apiBaseUrl, projectId],
    queryFn: ({ signal }) => listMapBuilds(apiBaseUrl, projectId as string, signal),
    enabled: mode === "api" && projectId != null,
    retry: false,
    staleTime: 5_000,
  });
}
