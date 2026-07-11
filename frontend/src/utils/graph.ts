import ELK from "elkjs/lib/elk.bundled.js";
import { MarkerType, type Edge, type Node } from "reactflow";
import type { GraphEdgeModel, GraphFilterModel, GraphNodeModel, GraphViewModel, ScanProgressEvent, TraceEvent } from "../types";
import { getLensMatches } from "./lenses";

export type FlowNodeData = GraphNodeModel & {
  isFocused: boolean;
  isDimmed: boolean;
  isSelected: boolean;
  isProgressTarget: boolean;
};

export type FlowEdgeData = GraphEdgeModel & {
  isFocused: boolean;
  isDimmed: boolean;
  isSelected: boolean;
  isProgressTarget: boolean;
  isUnmapped: boolean;
  routeOffset: number;
  sourceYOffset: number;
  targetYOffset: number;
  labelLaneOffset: number;
  labelStackOffset: number;
  labelSide: "above" | "below";
};

const elk = new ELK();
const NODE_WIDTH = 208;
const NODE_HEIGHT = 88;

function getLaneOffsets(edges: GraphEdgeModel[], key: "from" | "to") {
  const groups = new Map<string, GraphEdgeModel[]>();

  edges.forEach((edge) => {
    groups.set(edge[key], [...(groups.get(edge[key]) ?? []), edge]);
  });

  return new Map(
    edges.map((edge) => {
      const group = groups.get(edge[key]) ?? [edge];
      const laneIndex = group.findIndex((item) => item.id === edge.id);
      const centeredIndex = Math.max(laneIndex, 0) - (group.length - 1) / 2;
      return [edge.id, centeredIndex * 22];
    }),
  );
}

function getLabelOffsets(edges: GraphEdgeModel[]): Map<string, { labelLaneOffset: number; labelStackOffset: number; labelSide: "above" | "below" }> {
  const groups = new Map<string, GraphEdgeModel[]>();

  edges.forEach((edge) => {
    const key = `${edge.from}->${edge.to}`;
    groups.set(key, [...(groups.get(key) ?? []), edge]);
  });

  return new Map(
    edges.map((edge) => {
      const group = groups.get(`${edge.from}->${edge.to}`) ?? [edge];
      const laneIndex = Math.max(group.findIndex((item) => item.id === edge.id), 0);
      const centeredIndex = laneIndex - (group.length - 1) / 2;

      return [
        edge.id,
        {
          labelLaneOffset: centeredIndex * 26,
          labelStackOffset: laneIndex % 2 === 0 ? 0 : 18,
          labelSide: laneIndex % 2 === 0 ? "above" : "below",
        },
      ];
    }),
  );
}

function getSourceRouteOffsets(edges: GraphEdgeModel[]) {
  const groups = new Map<string, GraphEdgeModel[]>();

  edges.forEach((edge) => {
    groups.set(edge.from, [...(groups.get(edge.from) ?? []), edge]);
  });

  return new Map(
    edges.map((edge) => {
      const group = groups.get(edge.from) ?? [edge];
      const laneIndex = group.findIndex((item) => item.id === edge.id);
      return [edge.id, 48 + Math.max(laneIndex, 0) * 30];
    }),
  );
}

export function makeGraphIndexes(graph: GraphViewModel) {
  const nodeIdBySource = new Map<string, string>();
  const edgeIdBySource = new Map<string, string>();

  graph.nodes.forEach((node) => {
    nodeIdBySource.set(node.id, node.id);
    if (node.source_id) nodeIdBySource.set(node.source_id, node.id);
  });

  graph.edges.forEach((edge) => {
    edgeIdBySource.set(edge.id, edge.id);
    if (edge.source_id) edgeIdBySource.set(edge.source_id, edge.id);
  });

  return { nodeIdBySource, edgeIdBySource };
}

export function getFilterMatches(filters: GraphFilterModel[], activeFilterIds: string[]) {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  const activeFilters = filters.filter((filter) => activeFilterIds.includes(filter.id));

  activeFilters.forEach((filter) => {
    filter.matches_node_ids.forEach((id) => nodeIds.add(id));
    filter.matches_edge_ids.forEach((id) => edgeIds.add(id));
  });

  // Only treat filters that actually exist in the payload as "active" so a default
  // filter id that the payload does not define cannot dim the entire graph on load.
  return { nodeIds, edgeIds, hasFilters: activeFilters.length > 0 };
}

export function getTraceFocus(event: TraceEvent | undefined, graph: GraphViewModel) {
  const { nodeIdBySource, edgeIdBySource } = makeGraphIndexes(graph);
  const focusedNodeIds = new Set<string>();
  const focusedEdgeIds = new Set<string>();

  if (!event) {
    return { focusedNodeIds, focusedEdgeIds };
  }

  if (event.component_id) {
    const nodeId = nodeIdBySource.get(event.component_id);
    if (nodeId) focusedNodeIds.add(nodeId);
  }

  if (event.unmapped_component_id) {
    const nodeId = nodeIdBySource.get(event.unmapped_component_id);
    if (nodeId) focusedNodeIds.add(nodeId);
  }

  if (event.edge_id) {
    const edgeId = edgeIdBySource.get(event.edge_id);
    if (edgeId) focusedEdgeIds.add(edgeId);
  }

  return { focusedNodeIds, focusedEdgeIds };
}

export function createFlowElements(
  graph: GraphViewModel,
  options: {
    activeFilterIds: string[];
    activeLensId?: string | null;
    selectedId?: string;
    selectedKind?: "node" | "edge";
    traceEvent?: TraceEvent;
    progressTargetId?: string;
  },
) {
  const filterMatches = getFilterMatches(graph.filters.available, options.activeFilterIds);
  // Lenses highlight and dim only — every canonical node and edge stays mounted.
  const lensMatches = getLensMatches(graph.filters.lenses, options.activeLensId ?? null);
  const traceFocus = getTraceFocus(options.traceEvent, graph);
  const hasTraceFocus = traceFocus.focusedNodeIds.size > 0 || traceFocus.focusedEdgeIds.size > 0;
  const hasHighlightScope = filterMatches.hasFilters || lensMatches.hasLens || hasTraceFocus;
  const sourceRouteOffsets = getSourceRouteOffsets(graph.edges);
  const labelOffsets = getLabelOffsets(graph.edges);
  const sourceYOffsets = getLaneOffsets(graph.edges, "from");
  const targetYOffsets = getLaneOffsets(graph.edges, "to");

  const nodes: Node<FlowNodeData>[] = graph.nodes.map((node) => {
    const selected = options.selectedKind === "node" && options.selectedId === node.id;
    const filterFocused = filterMatches.nodeIds.has(node.id);
    const lensFocused = lensMatches.nodeIds.has(node.id);
    const traceFocused = traceFocus.focusedNodeIds.has(node.id);
    const progressFocused = options.progressTargetId === node.id;
    const focused = selected || filterFocused || lensFocused || traceFocused || progressFocused;
    const dimmed = hasHighlightScope && !focused;

    return {
      id: node.id,
      type: "systemNode",
      position: { x: 0, y: 0 },
      data: {
        ...node,
        isFocused: focused,
        isDimmed: dimmed,
        isSelected: selected,
        isProgressTarget: progressFocused,
      },
    };
  });

  const edges: Edge<FlowEdgeData>[] = graph.edges.map((edge) => {
    const selected = options.selectedKind === "edge" && options.selectedId === edge.id;
    const filterFocused = filterMatches.edgeIds.has(edge.id);
    const lensFocused = lensMatches.edgeIds.has(edge.id);
    const traceFocused = traceFocus.focusedEdgeIds.has(edge.id);
    const progressFocused = options.progressTargetId === edge.id;
    const focused = selected || filterFocused || lensFocused || traceFocused || progressFocused;
    const dimmed = hasHighlightScope && !focused;
    const labelOffset = labelOffsets.get(edge.id);
    const isRisk = edge.risk_hint_ids.length > 0;
    const isUnmapped = edge.status === "needs_confirmation";
    const strokeColor = focused
      ? "var(--accent)"
      : isRisk
        ? "var(--risk)"
        : isUnmapped
          ? "var(--unmapped)"
          : "var(--line-strong)";

    return {
      id: edge.id,
      source: edge.from,
      target: edge.to,
      type: "ordered",
      animated: false,
      label: edge.label ?? edge.relationship ?? undefined,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 18,
        height: 18,
        color: strokeColor,
      },
      data: {
        ...edge,
        isFocused: focused,
        isDimmed: dimmed,
        isSelected: selected,
        isProgressTarget: progressFocused,
        isUnmapped,
        routeOffset: sourceRouteOffsets.get(edge.id) ?? 48,
        sourceYOffset: sourceYOffsets.get(edge.id) ?? 0,
        targetYOffset: targetYOffsets.get(edge.id) ?? 0,
        labelLaneOffset: labelOffset?.labelLaneOffset ?? 0,
        labelStackOffset: labelOffset?.labelStackOffset ?? 0,
        labelSide: labelOffset?.labelSide ?? "above",
      },
      style: {
        stroke: strokeColor,
        strokeWidth: focused ? 2.4 : 1.6,
        opacity: dimmed ? 0.18 : 1,
        strokeDasharray: isUnmapped ? "5 4" : undefined,
      },
    };
  });

  return { nodes, edges };
}

const ATTACHMENT_STACK_GAP = 26;
const ATTACHMENT_X_OFFSET = 18;

function resolveAttachmentAnchorId(data: FlowNodeData, layoutNodeIds: Set<string>): string | null {
  if (data.primary_anchor_node_id && layoutNodeIds.has(data.primary_anchor_node_id)) {
    return data.primary_anchor_node_id;
  }
  return data.anchor_node_ids.find((id) => layoutNodeIds.has(id)) ?? null;
}

export async function layoutGraph(nodes: Node<FlowNodeData>[], edges: Edge<FlowEdgeData>[]) {
  // Profile attachments are backend-anchored overlays, not flow participants:
  // they stay out of the layered layout and sit beside their anchor node. An
  // attachment whose anchor cannot be resolved degrades into the main layout
  // so it never disappears.
  const layoutNodeIds = new Set(
    nodes.filter((node) => node.data.semantic_kind !== "profile_attachment").map((node) => node.id),
  );
  const anchorByAttachmentId = new Map<string, string>();
  nodes.forEach((node) => {
    if (node.data.semantic_kind !== "profile_attachment") return;
    const anchorId = resolveAttachmentAnchorId(node.data, layoutNodeIds);
    if (anchorId) anchorByAttachmentId.set(node.id, anchorId);
  });

  const layoutNodes = nodes.filter((node) => !anchorByAttachmentId.has(node.id));
  const layoutEdges = edges.filter(
    (edge) => !anchorByAttachmentId.has(edge.source) && !anchorByAttachmentId.has(edge.target),
  );

  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "54",
      "elk.layered.spacing.nodeNodeBetweenLayers": "118",
      "elk.edgeRouting": "ORTHOGONAL",
    },
    children: layoutNodes.map((node) => ({
      id: node.id,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    })),
    edges: layoutEdges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };

  const layout = await elk.layout(elkGraph);
  const positions = new Map(layout.children?.map((node) => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }]) ?? []);

  const stackSizeByAnchorId = new Map<string, number>();
  anchorByAttachmentId.forEach((anchorId, attachmentId) => {
    const anchorPosition = positions.get(anchorId);
    if (!anchorPosition) return;
    const stackIndex = stackSizeByAnchorId.get(anchorId) ?? 0;
    stackSizeByAnchorId.set(anchorId, stackIndex + 1);
    positions.set(attachmentId, {
      x: anchorPosition.x + ATTACHMENT_X_OFFSET,
      y: anchorPosition.y - (NODE_HEIGHT + ATTACHMENT_STACK_GAP) * (stackIndex + 1),
    });
  });

  return nodes.map((node) => ({
    ...node,
    position: positions.get(node.id) ?? node.position,
  }));
}

export function createProgressTargets(graph: GraphViewModel) {
  return [
    ...graph.nodes.map((node) => ({ id: node.id, label: node.label, kind: "node" as const })),
    ...graph.edges.map((edge) => ({ id: edge.id, label: edge.label ?? edge.relationship ?? edge.id, kind: "edge" as const })),
  ];
}

export function resolveProgressTargetId(event: ScanProgressEvent | null, graph: GraphViewModel): string | undefined {
  if (!event) return undefined;

  const { nodeIdBySource, edgeIdBySource } = makeGraphIndexes(graph);

  if (event.node_id) {
    return nodeIdBySource.get(event.node_id) ?? event.node_id;
  }

  if (event.edge_id) {
    return edgeIdBySource.get(event.edge_id) ?? event.edge_id;
  }

  if (event.component_id) {
    return nodeIdBySource.get(event.component_id) ?? event.component_id;
  }

  if (event.source_id) {
    return nodeIdBySource.get(event.source_id) ?? edgeIdBySource.get(event.source_id) ?? event.source_id;
  }

  if (event.slot) {
    return graph.nodes.find((node) => node.slot === event.slot)?.id;
  }

  return undefined;
}
