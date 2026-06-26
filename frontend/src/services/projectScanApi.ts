import {
  projectImportResponseSchema,
  scanCreateResponseSchema,
  type ProjectImportResponse,
  type ScanBoundaryDecision,
  type ScanCreateResponse,
} from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

type StartScanOptions = {
  projectId: string;
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

export async function startProjectScan(baseUrl: string, options: StartScanOptions): Promise<ScanCreateResponse> {
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: options.projectId,
      boundary_decisions: options.boundaryDecisions ?? [],
    }),
  });
  return scanCreateResponseSchema.parse(payload);
}
