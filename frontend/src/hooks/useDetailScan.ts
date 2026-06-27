import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createDetailScan, detailScanRequest, type DetailScanTarget } from "../services/detailScanApi";
import { loadApiViewerPayload } from "../services/viewerApi";
import type { DetailScanDepth, DetailScanResponse, ViewerPayload } from "../types";

type RunDetailScanOptions = {
  projectId: string;
  target: DetailScanTarget;
  scanDepth: DetailScanDepth;
};

export type DetailScanRunResult = {
  response: DetailScanResponse;
  refreshedPayload?: ViewerPayload;
  refreshError?: string;
};

export function useDetailScan(apiBaseUrl: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async ({ projectId, target, scanDepth }: RunDetailScanOptions): Promise<DetailScanRunResult> => {
      const response = await createDetailScan(apiBaseUrl, detailScanRequest(projectId, target, scanDepth));

      try {
        const refreshedPayload = await loadApiViewerPayload(apiBaseUrl);
        return { response, refreshedPayload };
      } catch (error) {
        return {
          response,
          refreshError:
            error instanceof Error
              ? `Detail scan completed, but the map could not be refreshed: ${error.message}`
              : "Detail scan completed, but the map could not be refreshed.",
        };
      }
    },
    onSuccess: (result) => {
      if (result.refreshedPayload) {
        queryClient.setQueryData(["viewer-load-result", "api", apiBaseUrl], result.refreshedPayload);
      }
    },
  });

  return {
    run: mutation.mutate,
    reset: mutation.reset,
    data: mutation.data,
    error: mutation.error instanceof Error ? mutation.error.message : undefined,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    variables: mutation.variables,
  };
}
