import { useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  BaseEdge,
  EdgeLabelRenderer,
  MiniMap,
  applyNodeChanges,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeChange,
  ReactFlowProvider,
  useReactFlow,
  useViewport,
} from "reactflow";
import "reactflow/dist/style.css";
import { Maximize, Minus, Plus } from "lucide-react";
import type { GraphViewModel, Selection, TraceEvent } from "../types";
import { createFlowElements, layoutGraph, makeGraphIndexes, type FlowEdgeData, type FlowNodeData } from "../utils/graph";
import { layoutPlaneBands, type PlaneBandModel } from "../utils/planes";
import { PlaneBandNode, type PlaneBandData } from "./PlaneBandNode";
import { SystemNode } from "./SystemNode";

const NODE_WIDTH = 208;
const NODE_HEIGHT = 88;
const MIN_FOLLOW_ZOOM = 0.62;
const prefersReducedMotion =
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const ANIMATION_DURATION = prefersReducedMotion ? 0 : 320;

const nodeTypes = {
  systemNode: SystemNode,
  planeBand: PlaneBandNode,
};

function OrderedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  style,
  label,
  data,
}: EdgeProps<FlowEdgeData>) {
  const startY = sourceY + (data?.sourceYOffset ?? 0);
  const endY = targetY + (data?.targetYOffset ?? 0);
  const xDirection = targetX >= sourceX ? 1 : -1;
  const yDirection = endY >= startY ? 1 : -1;
  const xDistance = Math.abs(targetX - sourceX);
  const yDistance = Math.abs(endY - startY);
  const routeOffset = Math.min(data?.routeOffset ?? 48, Math.max(32, xDistance - 16));
  const laneX = sourceX + routeOffset * xDirection;
  const cornerRadius = Math.min(10, Math.max(0, yDistance / 2), Math.max(0, Math.abs(targetX - laneX) / 2));
  const edgePath =
    yDistance < 8
      ? `M ${sourceX},${startY} L ${targetX},${endY}`
      : [
          `M ${sourceX},${startY}`,
          `L ${laneX},${startY}`,
          `Q ${laneX},${startY} ${laneX},${startY + cornerRadius * yDirection}`,
          `L ${laneX},${endY - cornerRadius * yDirection}`,
          `Q ${laneX},${endY} ${laneX + cornerRadius * xDirection},${endY}`,
          `L ${targetX},${endY}`,
        ].join(" ");
  const labelX = yDistance < 8 ? (sourceX + targetX) / 2 : laneX + (data?.labelLaneOffset ?? 0);
  const labelY =
    yDistance < 8
      ? startY - 20 - (data?.labelStackOffset ?? 0)
      : startY + (endY - startY) * 0.45 + (data?.labelStackOffset ?? 0);

  return (
    <>
      <BaseEdge id={id} markerEnd={markerEnd} path={edgePath} style={style} />
      {label ? (
        <EdgeLabelRenderer>
          <div
            className={[
              "edge-label-pill",
              data?.isFocused ? "is-focused" : "",
              data?.isDimmed ? "is-dimmed" : "",
              data?.isUnmapped ? "is-unmapped" : "",
              data?.labelSide === "below" ? "is-below" : "",
            ].join(" ")}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
            title={data?.label ?? data?.relationship ?? "flow"}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}

const edgeTypes = {
  ordered: OrderedEdge,
};

function CanvasControls() {
  const reactFlow = useReactFlow();
  return (
    <div className="canvas-controls">
      <button className="icon-btn" type="button" aria-label="Zoom in" title="Zoom in" onClick={() => reactFlow.zoomIn()}>
        <Plus size={15} />
      </button>
      <button className="icon-btn" type="button" aria-label="Zoom out" title="Zoom out" onClick={() => reactFlow.zoomOut()}>
        <Minus size={15} />
      </button>
      <button
        className="icon-btn"
        type="button"
        aria-label="Fit to view"
        title="Fit to view"
        onClick={() => reactFlow.fitView({ padding: 0.22, duration: ANIMATION_DURATION })}
      >
        <Maximize size={15} />
      </button>
    </div>
  );
}

function ZoomHint() {
  const { zoom } = useViewport();
  return <div className="canvas-hint">{Math.round(zoom * 100)}%</div>;
}

function resolveEdgeTargetNodeId(graph: GraphViewModel, edgeId: string | undefined) {
  if (!edgeId) return null;

  const edge = graph.edges.find((item) => item.id === edgeId);
  return edge?.to ?? edge?.from ?? null;
}

function resolveFollowNodeId({
  graph,
  selected,
  traceEvent,
  progressTargetId,
}: {
  graph: GraphViewModel;
  selected: Selection;
  traceEvent?: TraceEvent;
  progressTargetId?: string;
}) {
  const nodeIds = new Set(graph.nodes.map((node) => node.id));
  const { nodeIdBySource, edgeIdBySource } = makeGraphIndexes(graph);

  if (progressTargetId) {
    if (nodeIds.has(progressTargetId)) return progressTargetId;
    const edgeTargetNodeId = resolveEdgeTargetNodeId(graph, progressTargetId);
    if (edgeTargetNodeId) return edgeTargetNodeId;
  }

  if (traceEvent?.component_id) {
    const nodeId = nodeIdBySource.get(traceEvent.component_id);
    if (nodeId) return nodeId;
  }

  if (traceEvent?.unmapped_component_id) {
    const nodeId = nodeIdBySource.get(traceEvent.unmapped_component_id);
    if (nodeId) return nodeId;
  }

  if (traceEvent?.edge_id) {
    const edgeId = edgeIdBySource.get(traceEvent.edge_id);
    const edgeTargetNodeId = resolveEdgeTargetNodeId(graph, edgeId);
    if (edgeTargetNodeId) return edgeTargetNodeId;
  }

  if (selected?.kind === "node") return selected.id;

  if (selected?.kind === "edge") {
    const edgeTargetNodeId = resolveEdgeTargetNodeId(graph, selected.id);
    if (edgeTargetNodeId) return edgeTargetNodeId;
  }

  return null;
}

type Props = {
  graph: GraphViewModel;
  /** "planes": fixed reference-map bands grouped by backend plane_id (stable
      layout, no dragging). "auto": legacy ELK layered layout. */
  layoutMode: "auto" | "planes";
  activeFilterIds: string[];
  activeLensId: string | null;
  selected: Selection;
  traceEvent?: TraceEvent;
  progressTargetId?: string;
  followFocus: boolean;
  fitSignal: number;
  onSelect: (selection: Selection) => void;
  onInteractingChange?: (interacting: boolean) => void;
};

function GraphCanvas({
  graph,
  layoutMode,
  activeFilterIds,
  activeLensId,
  selected,
  traceEvent,
  progressTargetId,
  followFocus,
  fitSignal,
  onSelect,
  onInteractingChange,
}: Props) {
  const selectedKind = selected?.kind === "node" || selected?.kind === "edge" ? selected.kind : undefined;
  const selectedId = selected?.kind === "node" || selected?.kind === "edge" ? selected.id : undefined;
  const [nodes, setNodes] = useState<Array<Node<FlowNodeData> | Node<PlaneBandData>>>([]);
  const [edges, setEdges] = useState<Edge<FlowEdgeData>[]>([]);
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [bands, setBands] = useState<PlaneBandModel[]>([]);
  const lastCenteredNodeId = useRef<string | null>(null);
  const lastFitGraphKey = useRef<string | null>(null);
  const reactFlow = useReactFlow();
  const followNodeId = useMemo(
    () => resolveFollowNodeId({ graph, selected, traceEvent, progressTargetId }),
    [graph, progressTargetId, selected, traceEvent],
  );
  const graphStructureKey = useMemo(
    () => [
      graph.nodes.map((node) => node.id).join("|"),
      graph.edges.map((edge) => `${edge.id}:${edge.from}->${edge.to}`).join("|"),
    ].join("::"),
    [graph.edges, graph.nodes],
  );

  const rawElements = useMemo(
    () =>
      createFlowElements(graph, {
        activeFilterIds,
        activeLensId,
        selectedId,
        selectedKind,
        traceEvent,
        progressTargetId,
      }),
    [activeFilterIds, activeLensId, graph, progressTargetId, selectedId, selectedKind, traceEvent],
  );

  useEffect(() => {
    let cancelled = false;
    const baseElements = createFlowElements(graph, {
      activeFilterIds: [],
    });

    if (layoutMode === "planes") {
      const planeLayout = layoutPlaneBands(baseElements.nodes);
      setPositions(Object.fromEntries(planeLayout.positions));
      setBands(planeLayout.bands);
      lastFitGraphKey.current = null;
      return;
    }

    setBands([]);
    layoutGraph(baseElements.nodes, baseElements.edges).then((layoutedNodes) => {
      if (!cancelled) {
        setPositions(Object.fromEntries(layoutedNodes.map((node) => [node.id, node.position])));
        lastFitGraphKey.current = null;
      }
    });

    return () => {
      cancelled = true;
    };
  }, [graph, graphStructureKey, layoutMode, reactFlow]);

  useEffect(() => {
    const hasPositions = Object.keys(positions).length > 0;
    const bandNodes: Node<PlaneBandData>[] = bands.map((band) => ({
      id: `plane-band:${band.id}`,
      type: "planeBand",
      position: { x: band.x, y: band.y },
      draggable: false,
      selectable: false,
      focusable: false,
      zIndex: -1,
      style: { width: band.width, height: band.height, pointerEvents: "none" },
      data: { label: band.label, sublabel: band.sublabel, count: band.count },
    }));
    setNodes([
      ...bandNodes,
      ...rawElements.nodes.map((node) => ({
        ...node,
        position: positions[node.id] ?? node.position,
        hidden: !positions[node.id],
      })),
    ]);
    // Withhold edges until nodes are positioned so they don't briefly route through (0,0).
    setEdges(hasPositions ? rawElements.edges : []);
  }, [bands, positions, rawElements]);

  const translateExtent = useMemo<[[number, number], [number, number]] | undefined>(() => {
    const points = Object.values(positions);
    if (points.length === 0) return undefined;

    const xs = points.map((point) => point.x);
    const ys = points.map((point) => point.y);
    const padding = 600;
    return [
      [Math.min(...xs) - padding, Math.min(...ys) - padding],
      [Math.max(...xs) + NODE_WIDTH + padding, Math.max(...ys) + NODE_HEIGHT + padding],
    ];
  }, [positions]);

  function handleNodesChange(changes: NodeChange[]) {
    setNodes((currentNodes) => applyNodeChanges(changes, currentNodes as Node[]) as typeof currentNodes);
  }

  function handleNodeDragStop(_: React.MouseEvent, node: Node<FlowNodeData>) {
    setPositions((currentPositions) => ({
      ...currentPositions,
      [node.id]: node.position,
    }));
    onInteractingChange?.(false);
  }

  // Toolbar "Reset" requests a fit; fitSignal starts at 0 (no fit on mount).
  useEffect(() => {
    if (fitSignal === 0 || nodes.length === 0) return;
    reactFlow.fitView({ padding: 0.22, duration: ANIMATION_DURATION });
  }, [fitSignal, nodes.length, reactFlow]);

  useEffect(() => {
    if (followFocus || nodes.length === 0 || lastFitGraphKey.current === graphStructureKey) return;
    if (Object.keys(positions).length < graph.nodes.length) return;

    lastFitGraphKey.current = graphStructureKey;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => reactFlow.fitView({ padding: 0.22, duration: ANIMATION_DURATION }));
    });
  }, [followFocus, graph.nodes.length, graphStructureKey, nodes.length, positions, reactFlow]);

  useEffect(() => {
    if (!followFocus || nodes.length === 0) {
      lastCenteredNodeId.current = null;
      return;
    }

    if (!followNodeId || !positions[followNodeId]) return;

    const focusNode = nodes.find((node) => node.id === followNodeId);
    const focusPosition = positions[followNodeId];
    if (!focusNode || !focusPosition || lastCenteredNodeId.current === focusNode.id) return;

    const nodeWidth = focusNode.width ?? NODE_WIDTH;
    const nodeHeight = focusNode.height ?? NODE_HEIGHT;
    lastCenteredNodeId.current = focusNode.id;

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        reactFlow.setCenter(focusPosition.x + nodeWidth / 2, focusPosition.y + nodeHeight / 2, {
          duration: ANIMATION_DURATION,
          zoom: Math.max(reactFlow.getZoom(), MIN_FOLLOW_ZOOM),
        });
      });
    });
  }, [followFocus, followNodeId, nodes, positions, reactFlow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      defaultViewport={{ x: 42, y: 132, zoom: 0.68 }}
      minZoom={0.32}
      maxZoom={1.45}
      translateExtent={translateExtent}
      nodesDraggable={layoutMode === "auto"}
      onNodesChange={handleNodesChange}
      onNodeDragStart={() => onInteractingChange?.(true)}
      onNodeDragStop={handleNodeDragStop}
      onMoveStart={() => onInteractingChange?.(true)}
      onMoveEnd={() => onInteractingChange?.(false)}
      panOnScroll
      selectionOnDrag
      onNodeClick={(_, node) => onSelect({ kind: "node", id: node.id })}
      onEdgeClick={(_, edge) => onSelect({ kind: "edge", id: edge.id })}
      onPaneClick={() => onSelect(null)}
    >
      <Background variant={BackgroundVariant.Dots} color="var(--grid)" gap={22} size={1.1} />
      <MiniMap
        pannable
        zoomable
        nodeStrokeWidth={2}
        nodeColor={(node) => (node.type === "planeBand" ? "var(--surface-2)" : "var(--line-strong)")}
        maskColor="var(--canvas)"
      />
      <CanvasControls />
      <ZoomHint />
    </ReactFlow>
  );
}

export function SystemGraph(props: Props) {
  return (
    <ReactFlowProvider>
      <GraphCanvas {...props} />
    </ReactFlowProvider>
  );
}
