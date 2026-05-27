import ELK from "elkjs/lib/elk.bundled.js";
import type { Edge, Node } from "reactflow";
import type { GraphEdgeModel, GraphFilterModel, GraphNodeModel, GraphViewModel, TraceEvent } from "../types";

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
};

const elk = new ELK();
const NODE_WIDTH = 230;
const NODE_HEIGHT = 96;

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

  filters
    .filter((filter) => activeFilterIds.includes(filter.id))
    .forEach((filter) => {
      filter.matches_node_ids.forEach((id) => nodeIds.add(id));
      filter.matches_edge_ids.forEach((id) => edgeIds.add(id));
    });

  return { nodeIds, edgeIds, hasFilters: activeFilterIds.length > 0 };
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
    selectedId?: string;
    selectedKind?: "node" | "edge";
    traceEvent?: TraceEvent;
    progressTargetId?: string;
  },
) {
  const filterMatches = getFilterMatches(graph.filters.available, options.activeFilterIds);
  const traceFocus = getTraceFocus(options.traceEvent, graph);
  const hasTraceFocus = traceFocus.focusedNodeIds.size > 0 || traceFocus.focusedEdgeIds.size > 0;

  const nodes: Node<FlowNodeData>[] = graph.nodes.map((node) => {
    const selected = options.selectedKind === "node" && options.selectedId === node.id;
    const filterFocused = filterMatches.nodeIds.has(node.id);
    const traceFocused = traceFocus.focusedNodeIds.has(node.id);
    const progressFocused = options.progressTargetId === node.id;
    const focused = selected || filterFocused || traceFocused || progressFocused;
    const dimmed = (filterMatches.hasFilters || hasTraceFocus) && !focused;

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
    const traceFocused = traceFocus.focusedEdgeIds.has(edge.id);
    const progressFocused = options.progressTargetId === edge.id;
    const focused = selected || filterFocused || traceFocused || progressFocused;
    const dimmed = (filterMatches.hasFilters || hasTraceFocus) && !focused;

    return {
      id: edge.id,
      source: edge.from,
      target: edge.to,
      type: "smoothstep",
      animated: traceFocused || progressFocused,
      label: edge.label,
      data: {
        ...edge,
        isFocused: focused,
        isDimmed: dimmed,
        isSelected: selected,
        isProgressTarget: progressFocused,
      },
      style: {
        stroke: focused ? "#0f8b8d" : "#9aa6b2",
        strokeWidth: focused ? 2.7 : 1.3,
        opacity: dimmed ? 0.22 : 0.82,
      },
      labelStyle: {
        fill: focused ? "#0b5557" : "#65717f",
        fontSize: 11,
        fontWeight: focused ? 700 : 500,
      },
    };
  });

  return { nodes, edges };
}

export async function layoutGraph(nodes: Node<FlowNodeData>[], edges: Edge<FlowEdgeData>[]) {
  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "42",
      "elk.layered.spacing.nodeNodeBetweenLayers": "88",
      "elk.edgeRouting": "ORTHOGONAL",
    },
    children: nodes.map((node) => ({
      id: node.id,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };

  const layout = await elk.layout(elkGraph);
  const positions = new Map(layout.children?.map((node) => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }]) ?? []);

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
