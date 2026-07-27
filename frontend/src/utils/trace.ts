import type { GraphViewModel, TraceEvent } from "../types";

export type TraceHighlight = {
  nodeIds: string[];
  edgeIds: string[];
  fallbackMessage: string | null;
};

export function sortTraceEvents(events: TraceEvent[]): TraceEvent[] {
  return [...events].sort((left, right) => {
    const sequenceDelta = left.sequence_index - right.sequence_index;
    return sequenceDelta !== 0 ? sequenceDelta : left.id.localeCompare(right.id);
  });
}

function boundedRef(value: string): string {
  return value.length > 72 ? `${value.slice(0, 69)}...` : value;
}

function exactNodeId(graph: GraphViewModel, sourceId: string): string | null {
  const matches = graph.nodes.filter(
    (node) => node.id === sourceId || node.source_id === sourceId || node.component_id === sourceId,
  );
  return matches.length === 1 ? matches[0].id : null;
}

function exactEdgeId(graph: GraphViewModel, sourceId: string): string | null {
  const matches = graph.edges.filter(
    (edge) => edge.id === sourceId || edge.source_id === sourceId || edge.flow_id === sourceId,
  );
  return matches.length === 1 ? matches[0].id : null;
}

export function resolveTraceHighlight(event: TraceEvent | undefined, graph: GraphViewModel): TraceHighlight {
  if (!event) return { nodeIds: [], edgeIds: [], fallbackMessage: null };

  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  const unresolved = new Set<string>();
  const nodeRefs = [event.component_id, event.unmapped_component_id].filter(
    (value): value is string => Boolean(value),
  );

  nodeRefs.forEach((sourceId) => {
    const nodeId = exactNodeId(graph, sourceId);
    if (nodeId) nodeIds.add(nodeId);
    else unresolved.add(sourceId);
  });

  if (event.edge_id) {
    const edgeId = exactEdgeId(graph, event.edge_id);
    if (edgeId) edgeIds.add(edgeId);
    else unresolved.add(event.edge_id);
  }

  if (event.endpoint_id && nodeIds.size === 0) {
    const endpoint = graph.endpoints.find((candidate) => candidate.endpoint_id === event.endpoint_id);
    if (endpoint?.component_id) {
      const nodeId = exactNodeId(graph, endpoint.component_id);
      if (nodeId) nodeIds.add(nodeId);
      else unresolved.add(endpoint.component_id);
    } else if (!event.component_id && !event.unmapped_component_id) {
      unresolved.add(event.endpoint_id);
    }
  }

  if (unresolved.size > 0) {
    const refs = [...unresolved].slice(0, 2).map(boundedRef).join(", ");
    return {
      nodeIds: [...nodeIds],
      edgeIds: [...edgeIds],
      fallbackMessage: `No exact architecture match for ${refs}. The map was left unchanged.`,
    };
  }

  if (nodeIds.size === 0 && edgeIds.size === 0) {
    return {
      nodeIds: [],
      edgeIds: [],
      fallbackMessage: "This event has no exact graph reference. The map was left unchanged.",
    };
  }

  return { nodeIds: [...nodeIds], edgeIds: [...edgeIds], fallbackMessage: null };
}

export function traceEventHasFailure(event: TraceEvent | undefined): boolean {
  if (!event) return false;
  const status = event.status?.toLocaleLowerCase();
  return Boolean(event.error) || ["blocked", "error", "failed", "partial", "timeout"].includes(status ?? "");
}

export function traceErrorLabel(error: unknown): string {
  if (typeof error === "string") return error;
  if (!error || typeof error !== "object") return "error";
  const record = error as Record<string, unknown>;
  if (typeof record.type === "string") return record.type;
  if (typeof record.code === "string") return record.code;
  return "error";
}
