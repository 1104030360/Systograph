import {
  projectImportResponseSchema,
  scanBoundaryDecisionSchema,
  scanCreateResponseSchema,
  scanInventoryPreflightRequestSchema,
  scanInventoryPreflightResponseSchema,
  type ProjectImportResponse,
  type ScanBoundaryDecision,
  type ScanCreateResponse,
  type ScanInventoryPreflightResponse,
} from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type CreateScanPreflightOptions = {
  projectId: string;
  requestedPaths?: string[];
  reviewableExcludedCursor?: string | null;
  reviewableExcludedLimit?: number;
};

export type StartScanOptions = {
  projectId: string;
  preflightRequestId: string;
  boundaryDecisions?: ScanBoundaryDecision[];
};

export async function importProject(baseUrl: string, projectPath: string): Promise<ProjectImportResponse> {
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/projects/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_type: "local_path",
      project_path: projectPath,
    }),
  });
  return projectImportResponseSchema.parse(payload);
}

export async function createScanPreflight(
  baseUrl: string,
  options: CreateScanPreflightOptions,
): Promise<ScanInventoryPreflightResponse> {
  const request = scanInventoryPreflightRequestSchema.parse({
    scan_depth: "system",
    requested_paths: options.requestedPaths ?? [],
    reviewable_excluded_cursor: options.reviewableExcludedCursor ?? null,
    reviewable_excluded_limit: options.reviewableExcludedLimit ?? 100,
  });
  const payload = await fetchJson(
    `${normalizeBaseUrl(baseUrl)}/api/projects/${encodeURIComponent(options.projectId)}/scan-preflights`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
  return scanInventoryPreflightResponseSchema.parse(payload);
}

export async function startProjectScan(baseUrl: string, options: StartScanOptions): Promise<ScanCreateResponse> {
  const boundaryDecisions = options.boundaryDecisions?.map((decision) => scanBoundaryDecisionSchema.parse(decision)) ?? [];
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: options.projectId,
      scan_depth: "system",
      preflight_request_id: options.preflightRequestId,
      boundary_decisions: boundaryDecisions,
    }),
  });
  return scanCreateResponseSchema.parse(payload);
}
