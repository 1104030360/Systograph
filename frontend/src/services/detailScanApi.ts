import {
  detailScanCreateRequestSchema,
  detailScanResponseSchema,
  viewerPayloadSchema,
  type DetailScanCreateRequest,
  type DetailScanDepth,
  type DetailScanResponse,
  type DetailScanTargetType,
  type GraphEdgeModel,
  type GraphNodeModel,
  type TraceEvent,
  type ViewerPayload,
} from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type DetailScanTarget = {
  targetType: DetailScanTargetType;
  target: string;
  label: string;
};

export class DetailScanContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DetailScanContractError";
  }
}

export async function createDetailScan(
  baseUrl: string,
  request: DetailScanCreateRequest,
  signal?: AbortSignal,
): Promise<DetailScanResponse> {
  const validated = detailScanCreateRequestSchema.parse(request);
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/detail-scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(validated),
    signal,
  });
  return detailScanResponseSchema.parse(payload);
}

export function detailScanRequest(
  projectId: string,
  buildId: string,
  target: DetailScanTarget,
  scanDepth: DetailScanDepth,
): DetailScanCreateRequest {
  return detailScanCreateRequestSchema.parse({
    project_id: projectId,
    build_id: buildId,
    target_type: target.targetType,
    target: target.target,
    scan_depth: scanDepth,
  });
}

/**
 * Build a target only from backend-declared canonical identity fields. Display
 * labels, badges, graph ids and string prefixes are deliberately ignored.
 */
export function targetForNode(node: GraphNodeModel): DetailScanTarget | null {
  if (node.semantic_kind === "unmapped_component" && node.source_id) {
    return { targetType: "unmapped_component", target: node.source_id, label: node.label };
  }
  if (node.semantic_kind === "repo_component" && node.component_id) {
    return { targetType: "component_instance", target: node.component_id, label: node.label };
  }
  return null;
}

export function targetForEdge(edge: GraphEdgeModel): DetailScanTarget | null {
  if (!edge.source_id) return null;
  return {
    targetType: "edge",
    target: edge.source_id,
    label: edge.label ?? edge.relationship ?? "Edge",
  };
}

export function targetForTrace(event: TraceEvent): DetailScanTarget | null {
  if (event.evidence_id) {
    return { targetType: "evidence", target: event.evidence_id, label: event.evidence_id };
  }
  if (event.edge_id) {
    return { targetType: "edge", target: event.edge_id, label: event.step_type ?? "Trace edge" };
  }
  if (event.unmapped_component_id) {
    return {
      targetType: "unmapped_component",
      target: event.unmapped_component_id,
      label: event.step_type ?? "Trace component",
    };
  }
  if (event.component_id) {
    return {
      targetType: "component_instance",
      target: event.component_id,
      label: event.step_type ?? "Trace component",
    };
  }
  return null;
}

export function targetForEvidence(evidenceId: string): DetailScanTarget {
  return { targetType: "evidence", target: evidenceId, label: evidenceId };
}

/**
 * The POST response already contains the child build projection. This bounded
 * adapter lets the UI switch to that immutable child even if the follow-up
 * build-scoped GET is temporarily unavailable; it never reads /api/map.
 */
export function viewerPayloadFromDetailScan(response: DetailScanResponse): ViewerPayload {
  const { build_id: buildId, scan_id: scanId, source_build_id: sourceBuildId, viewer_load_result: viewer } = response;
  if (!buildId || !scanId || !sourceBuildId || !viewer) {
    throw new DetailScanContractError("Detail Scan response did not publish complete child-build identity.");
  }

  const graph = viewer.graph_view_model;
  for (const [label, value] of [
    ["project_id", graph.project_id],
    ["scan_id", graph.scan_id],
    ["build_id", graph.build_id],
  ] as const) {
    const expected = label === "project_id" ? response.project_id : label === "scan_id" ? scanId : buildId;
    if (value !== expected) {
      throw new DetailScanContractError(`Child graph ${label} does not match the Detail Scan response.`);
    }
  }

  for (const [label, map] of [
    ["response", response.ai_system_map],
    ["viewer", viewer.ai_system_map],
  ] as const) {
    const project = map.project;
    const projectId =
      project && typeof project === "object" && "project_id" in project
        ? project.project_id
        : undefined;
    if (
      projectId !== response.project_id ||
      map.scan_id !== scanId ||
      map.build_id !== buildId ||
      map.generated_from_build_id !== buildId
    ) {
      throw new DetailScanContractError(`Child ${label} map identity does not match the Detail Scan response.`);
    }
  }

  return viewerPayloadSchema.parse({
    contract_source: "phase2-build",
    viewer_load_result: {
      loaded: viewer.loaded,
      error_reason: viewer.error_reason ?? null,
      warnings: response.warnings,
      project_id: response.project_id,
      scan_id: scanId,
      build_id: buildId,
      environment_id: graph.environment_id ?? null,
      generated_from_build_id: graph.generated_from_build_id ?? buildId,
      based_on_build_id: sourceBuildId,
      applied_mapping_ids: [],
      artifact_refs: [],
      map_json: viewer.map_json ?? null,
      ai_system_map: viewer.ai_system_map,
      profile_inference_result: null,
      readiness_report: null,
      graph_view_model: graph,
    },
  });
}
