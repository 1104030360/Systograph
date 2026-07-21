import type { PrototypeIconKind } from "./PrototypeIcon";

export const PLANE_PROTOTYPE_ICON_KINDS: Record<string, PrototypeIconKind> = {
  input_intent: "overview",
  control: "control",
  ingestion_indexing: "ingestion",
  retrieval: "retrieval",
  extension_subsystems: "extension",
  evidence: "extension",
  generation: "overview",
  memory_state: "memory",
  governance_observability: "governance",
  deployment_topology: "topology",
};

export function getPlanePrototypeIconKind(
  planeId: string | null | undefined,
): PrototypeIconKind | undefined {
  if (!planeId) return undefined;
  return PLANE_PROTOTYPE_ICON_KINDS[planeId];
}
