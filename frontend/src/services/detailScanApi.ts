import {
  detailScanCreateRequestSchema,
  detailScanResponseSchema,
  type DetailScanCreateRequest,
  type DetailScanDepth,
  type DetailScanResponse,
  type DetailScanTargetType,
  type GraphEdgeModel,
  type GraphNodeModel,
  type TraceEvent,
} from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type DetailScanTarget = {
  targetType: DetailScanTargetType;
  target: string;
  label: string;
};

export async function createDetailScan(
  baseUrl: string,
  request: DetailScanCreateRequest,
): Promise<DetailScanResponse> {
  const validated = detailScanCreateRequestSchema.parse(request);
  const payload = await fetchJson(`${normalizeBaseUrl(baseUrl)}/api/detail-scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(validated),
  });
  return detailScanResponseSchema.parse(payload);
}

export async function getDetailScan(baseUrl: string, detailScanId: string): Promise<DetailScanResponse> {
  const payload = await fetchJson(
    `${normalizeBaseUrl(baseUrl)}/api/detail-scans/${encodeURIComponent(detailScanId)}`,
  );
  return detailScanResponseSchema.parse(payload);
}

export function detailScanRequest(
  projectId: string,
  target: DetailScanTarget,
  scanDepth: DetailScanDepth,
): DetailScanCreateRequest {
  return detailScanCreateRequestSchema.parse({
    project_id: projectId,
    target_type: target.targetType,
    target: target.target,
    scan_depth: scanDepth,
  });
}

export function targetForNode(node: GraphNodeModel): DetailScanTarget | null {
  const sourceId = node.source_id?.trim();
  if (!sourceId) return null;

  if (node.type === "component_slot") {
    return { targetType: "component_slot", target: sourceId, label: node.label };
  }
  if (node.badges.includes("extension") || sourceId.startsWith("extension:")) {
    return { targetType: "extension", target: sourceId, label: node.label };
  }
  if (node.badges.includes("unmapped") || sourceId.startsWith("unmapped:")) {
    return { targetType: "unmapped_component", target: sourceId, label: node.label };
  }
  return { targetType: "component_instance", target: sourceId, label: node.label };
}

export function targetForEdge(edge: GraphEdgeModel): DetailScanTarget | null {
  const sourceId = edge.source_id?.trim();
  if (!sourceId) return null;
  return { targetType: "edge", target: sourceId, label: edge.label ?? edge.relationship ?? "Edge" };
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
  if (event.slot) {
    return { targetType: "component_slot", target: event.slot, label: event.step_type ?? event.slot };
  }
  return null;
}

export function targetForEvidence(evidenceId: string): DetailScanTarget {
  return { targetType: "evidence", target: evidenceId, label: evidenceId };
}
