import type { GraphNodeModel } from "../types";

export type NodeStatusKey =
  | "risk"
  | "needs_review"
  | "needs_confirmation"
  | "not_applicable"
  | "not_configured"
  | "missing"
  | "confirmed"
  | "confirmed_non_baseline"
  | "detected"
  | "partial"
  | "undetermined"
  | "not_detected"
  | "conflicted";

const MISSING_REQUIRED_SLOT_RISK_PREFIX = "risk:missing_required_slot:";
const PHASE2_STATUSES = new Set<NodeStatusKey>([
  "detected",
  "partial",
  "undetermined",
  "not_detected",
  "conflicted",
  "needs_review",
  "confirmed_non_baseline",
]);

export const PHASE2_STATUS_LEGEND: Array<{ key: NodeStatusKey; label: string }> = [
  { key: "detected", label: "Detected" },
  { key: "partial", label: "Partial" },
  { key: "undetermined", label: "Undetermined" },
  { key: "not_detected", label: "Not detected" },
  { key: "conflicted", label: "Conflicted" },
  { key: "needs_review", label: "Needs review" },
];

export function hasNodeLevelRisk(data: Pick<GraphNodeModel, "risk_hint_ids">) {
  return data.risk_hint_ids.some((riskId) => !riskId.startsWith(MISSING_REQUIRED_SLOT_RISK_PREFIX));
}

export function nodeStatusKey(data: Pick<GraphNodeModel, "risk_hint_ids" | "status">): NodeStatusKey {
  if (data.status && PHASE2_STATUSES.has(data.status as NodeStatusKey)) {
    return data.status as NodeStatusKey;
  }
  if (hasNodeLevelRisk(data)) return "risk";
  if (data.status === "needs_confirmation") return "needs_confirmation";
  if (data.status === "not_applicable") return "not_applicable";
  if (data.status === "not_configured") return "not_configured";
  if (data.status === "missing") return "missing";
  if (data.status === "confirmed") return "confirmed";
  return "detected";
}

export function nodeStatusLabel(status: NodeStatusKey): string {
  return status.replace(/_/g, " ");
}
