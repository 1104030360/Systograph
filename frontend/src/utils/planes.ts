import type { Node } from "reactflow";
import type { FlowNodeData } from "./graph";

/* Plane membership belongs to the backend (node.plane_id, catalog plan 01A).
   This module only decides where a backend-declared plane sits on screen:
   band order, labels, and card positions inside each band. Nodes whose payload
   publishes no plane_id degrade into a single "unassigned" band instead of
   being guessed into a plane. */
export const PLANE_PRESENTATION_ORDER = [
  "input_intent",
  "control",
  "ingestion_indexing",
  "retrieval",
  "extension_subsystems",
  "evidence",
  "generation",
  "memory_state",
  "governance_observability",
  "deployment_topology",
] as const;

const PLANE_LABELS: Record<string, string> = {
  input_intent: "Input & Intent",
  control: "Control",
  ingestion_indexing: "Ingestion & Indexing",
  retrieval: "Retrieval",
  extension_subsystems: "Extension Subsystems",
  evidence: "Evidence",
  generation: "Generation",
  memory_state: "Memory & State",
  governance_observability: "Governance & Observability",
  deployment_topology: "Deployment Topology",
};

export const UNASSIGNED_PLANE_ID = "__unassigned__";

export type PlaneBandModel = {
  id: string;
  label: string;
  sublabel: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  count: number;
};

const NODE_WIDTH = 208;
const NODE_HEIGHT = 88;
const MAX_COLUMNS = 6;
const BAND_GAP = 44;
const BAND_HEADER_HEIGHT = 46;
const BAND_PADDING_X = 26;
const BAND_PADDING_BOTTOM = 24;
const CARD_GAP_X = 26;
const CARD_GAP_Y = 30;
const ATTACHMENT_STACK_GAP = 22;
const ATTACHMENT_X_OFFSET = 18;

export function planeLabel(planeId: string): string {
  if (planeId === UNASSIGNED_PLANE_ID) return "Unassigned components";
  return (
    PLANE_LABELS[planeId] ??
    planeId.replace(/[_:-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

function resolveAnchorId(data: FlowNodeData, candidateIds: Set<string>): string | null {
  if (data.primary_anchor_node_id && candidateIds.has(data.primary_anchor_node_id)) {
    return data.primary_anchor_node_id;
  }
  return data.anchor_node_ids.find((id) => candidateIds.has(id)) ?? null;
}

export function layoutPlaneBands(nodes: Node<FlowNodeData>[]) {
  const positions = new Map<string, { x: number; y: number }>();
  const bands: PlaneBandModel[] = [];

  const bandCandidateIds = new Set(
    nodes.filter((node) => node.data.semantic_kind !== "profile_attachment").map((node) => node.id),
  );
  const anchorByAttachmentId = new Map<string, string>();
  nodes.forEach((node) => {
    if (node.data.semantic_kind !== "profile_attachment") return;
    const anchorId = resolveAnchorId(node.data, bandCandidateIds);
    if (anchorId) anchorByAttachmentId.set(node.id, anchorId);
  });

  const attachmentsByAnchorId = new Map<string, string[]>();
  anchorByAttachmentId.forEach((anchorId, attachmentId) => {
    attachmentsByAnchorId.set(anchorId, [...(attachmentsByAnchorId.get(anchorId) ?? []), attachmentId]);
  });

  // Band membership: everything except anchored attachments, keyed by the
  // backend-provided plane id; payload order inside a band is preserved.
  const bandNodesByPlaneId = new Map<string, Node<FlowNodeData>[]>();
  nodes.forEach((node) => {
    if (anchorByAttachmentId.has(node.id)) return;
    const planeId = node.data.plane_id ?? UNASSIGNED_PLANE_ID;
    bandNodesByPlaneId.set(planeId, [...(bandNodesByPlaneId.get(planeId) ?? []), node]);
  });

  const knownOrder = PLANE_PRESENTATION_ORDER.filter((planeId) => bandNodesByPlaneId.has(planeId));
  const extraOrder = [...bandNodesByPlaneId.keys()].filter(
    (planeId) =>
      planeId !== UNASSIGNED_PLANE_ID &&
      !(PLANE_PRESENTATION_ORDER as readonly string[]).includes(planeId),
  );
  const orderedPlaneIds = [
    ...knownOrder,
    ...extraOrder,
    ...(bandNodesByPlaneId.has(UNASSIGNED_PLANE_ID) ? [UNASSIGNED_PLANE_ID] : []),
  ];

  const maxColumns = Math.max(
    1,
    ...orderedPlaneIds.map((planeId) => Math.min((bandNodesByPlaneId.get(planeId) ?? []).length, MAX_COLUMNS)),
  );
  const bandWidth = BAND_PADDING_X * 2 + maxColumns * NODE_WIDTH + (maxColumns - 1) * CARD_GAP_X;

  let bandY = 0;
  orderedPlaneIds.forEach((planeId) => {
    const bandNodes = bandNodesByPlaneId.get(planeId) ?? [];
    const maxStack = Math.max(
      0,
      ...bandNodes.map((node) => attachmentsByAnchorId.get(node.id)?.length ?? 0),
    );
    const contentTop = BAND_HEADER_HEIGHT + maxStack * (NODE_HEIGHT + ATTACHMENT_STACK_GAP);
    const rows = Math.ceil(bandNodes.length / MAX_COLUMNS);

    bandNodes.forEach((node, index) => {
      const column = index % MAX_COLUMNS;
      const row = Math.floor(index / MAX_COLUMNS);
      positions.set(node.id, {
        x: BAND_PADDING_X + column * (NODE_WIDTH + CARD_GAP_X),
        y: bandY + contentTop + row * (NODE_HEIGHT + CARD_GAP_Y),
      });
    });

    const bandHeight =
      contentTop + rows * NODE_HEIGHT + Math.max(0, rows - 1) * CARD_GAP_Y + BAND_PADDING_BOTTOM;

    bands.push({
      id: planeId,
      label: planeLabel(planeId),
      sublabel: planeId === UNASSIGNED_PLANE_ID ? "plane not published by this build" : null,
      x: 0,
      y: bandY,
      width: bandWidth,
      height: bandHeight,
      count: bandNodes.length,
    });

    bandY += bandHeight + BAND_GAP;
  });

  anchorByAttachmentId.forEach((anchorId, attachmentId) => {
    const anchorPosition = positions.get(anchorId);
    if (!anchorPosition) return;
    const stackIndex = (attachmentsByAnchorId.get(anchorId) ?? []).indexOf(attachmentId);
    positions.set(attachmentId, {
      x: anchorPosition.x + ATTACHMENT_X_OFFSET,
      y: anchorPosition.y - (NODE_HEIGHT + ATTACHMENT_STACK_GAP) * (Math.max(stackIndex, 0) + 1),
    });
  });

  return { positions, bands };
}
