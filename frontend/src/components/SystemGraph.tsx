import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
  ReactFlowProvider,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphViewModel, Selection, TraceEvent } from "../types";
import { createFlowElements, layoutGraph, type FlowEdgeData, type FlowNodeData } from "../utils/graph";
import { SystemNode } from "./SystemNode";

const nodeTypes = {
  systemNode: SystemNode,
};

type Props = {
  graph: GraphViewModel;
  activeFilterIds: string[];
  selected: Selection;
  traceEvent?: TraceEvent;
  progressTargetId?: string;
  onSelect: (selection: Selection) => void;
};

function GraphCanvas({ graph, activeFilterIds, selected, traceEvent, progressTargetId, onSelect }: Props) {
  const selectedKind = selected?.kind === "node" || selected?.kind === "edge" ? selected.kind : undefined;
  const selectedId = selected?.kind === "node" || selected?.kind === "edge" ? selected.id : undefined;
  const [nodes, setNodes] = useState<Node<FlowNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge<FlowEdgeData>[]>([]);
  const reactFlow = useReactFlow();

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

    layoutGraph(rawElements.nodes, rawElements.edges).then((layoutedNodes) => {
      if (!cancelled) {
        setNodes(layoutedNodes);
        setEdges(rawElements.edges);
        window.requestAnimationFrame(() => {
          const focusedNodes = layoutedNodes.filter((node) => node.data.isFocused);
          if (focusedNodes.length > 0) {
            const minX = Math.min(...focusedNodes.map((node) => node.position.x));
            const minY = Math.min(...focusedNodes.map((node) => node.position.y));
            reactFlow.setViewport({ x: 56 - minX * 0.68, y: 130 - minY * 0.68, zoom: 0.68 }, { duration: 300 });
            return;
          }

          reactFlow.fitView({ padding: 0.2, duration: 300 });
        });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [rawElements, reactFlow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
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
