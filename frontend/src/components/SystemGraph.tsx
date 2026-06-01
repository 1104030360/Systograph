import { useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  MiniMap,
  type Edge,
  type EdgeProps,
  type Node,
  ReactFlowProvider,
  getSmoothStepPath,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphViewModel, Selection, TraceEvent } from "../types";
import { createFlowElements, layoutGraph, type FlowEdgeData, type FlowNodeData } from "../utils/graph";
import { SystemNode } from "./SystemNode";

const nodeTypes = {
  systemNode: SystemNode,
};

function OrderedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
  label,
  data,
}: EdgeProps<FlowEdgeData>) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const labelOffset = Math.abs(targetY - sourceY) < 24 || sourceY <= targetY ? -18 : 18;

  return (
    <>
      <BaseEdge id={id} markerEnd={markerEnd} path={edgePath} style={style} />
      <EdgeLabelRenderer>
        <div
          className={["edge-label-pill", data?.isFocused ? "is-focused" : "", data?.isDimmed ? "is-dimmed" : ""].join(" ")}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY + labelOffset}px)`,
          }}
          title={data?.label ?? data?.relationship ?? "flow"}
        >
          {label}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const edgeTypes = {
  ordered: OrderedEdge,
};

type Props = {
  graph: GraphViewModel;
  activeFilterIds: string[];
  selected: Selection;
  traceEvent?: TraceEvent;
  progressTargetId?: string;
  followFocus: boolean;
  onSelect: (selection: Selection) => void;
};

function GraphCanvas({ graph, activeFilterIds, selected, traceEvent, progressTargetId, followFocus, onSelect }: Props) {
  const selectedKind = selected?.kind === "node" || selected?.kind === "edge" ? selected.kind : undefined;
  const selectedId = selected?.kind === "node" || selected?.kind === "edge" ? selected.id : undefined;
  const [nodes, setNodes] = useState<Node<FlowNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge<FlowEdgeData>[]>([]);
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const lastCenteredNodeId = useRef<string | null>(null);
  const reactFlow = useReactFlow();
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
        selectedId,
        selectedKind,
        traceEvent,
        progressTargetId,
      }),
    [activeFilterIds, graph, progressTargetId, selectedId, selectedKind, traceEvent],
  );

  useEffect(() => {
    let cancelled = false;
    const baseElements = createFlowElements(graph, {
      activeFilterIds: [],
    });

    layoutGraph(baseElements.nodes, baseElements.edges).then((layoutedNodes) => {
      if (!cancelled) {
        setPositions(Object.fromEntries(layoutedNodes.map((node) => [node.id, node.position])));
        window.requestAnimationFrame(() => {
          window.requestAnimationFrame(() => reactFlow.fitView({ padding: 0.18, duration: 300 }));
        });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [graph, graphStructureKey, reactFlow]);

  useEffect(() => {
    setNodes(rawElements.nodes.map((node) => ({ ...node, position: positions[node.id] ?? node.position })));
    setEdges(rawElements.edges);
  }, [positions, rawElements]);

  useEffect(() => {
    if (!followFocus || nodes.length === 0) {
      lastCenteredNodeId.current = null;
      return;
    }

    const focusNode =
      nodes.find((node) => node.data.isProgressTarget) ??
      nodes.find((node) => node.data.isSelected) ??
      nodes.find((node) => node.data.isFocused);

    if (!focusNode || lastCenteredNodeId.current === focusNode.id) return;

    lastCenteredNodeId.current = focusNode.id;
    reactFlow.setCenter(
      focusNode.position.x + (focusNode.width ?? 230) / 2,
      focusNode.position.y + (focusNode.height ?? 96) / 2,
      { duration: 280, zoom: Math.max(reactFlow.getZoom(), 0.74) },
    );
  }, [followFocus, nodes, reactFlow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      defaultViewport={{ x: 42, y: 132, zoom: 0.68 }}
      minZoom={0.28}
      maxZoom={1.35}
      nodesDraggable
      panOnScroll
      selectionOnDrag
      onNodeClick={(_, node) => onSelect({ kind: "node", id: node.id })}
      onEdgeClick={(_, edge) => onSelect({ kind: "edge", id: edge.id })}
      onPaneClick={() => onSelect(null)}
    >
      <Background color="#d6dde4" gap={24} size={1} />
      <MiniMap pannable zoomable nodeStrokeWidth={3} />
      <Controls position="bottom-left" />
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
