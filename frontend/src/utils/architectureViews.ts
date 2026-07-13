import type { GraphViewModel } from "../types";

export type ArchitectureViewId =
  | "overview"
  | "dataflow"
  | "control"
  | "ingestion"
  | "retrieval"
  | "memory"
  | "governance"
  | "runtime"
  | "variants"
  | "known"
  | "extensions"
  | "unmapped"
  | "reasoning"
  | "topology"
  | "source"
  | "risk";

export type ArchitectureViewModel = {
  id: ArchitectureViewId;
  label: string;
  description: string;
  supported: boolean;
  unavailableReason: string | null;
  matchesNodeIds: string[];
  matchesEdgeIds: string[];
};

type ViewDefinition = Pick<ArchitectureViewModel, "id" | "label" | "description">;

export const ARCHITECTURE_VIEW_DEFINITIONS: ViewDefinition[] = [
  { id: "overview", label: "Overview", description: "The complete backend projection" },
  { id: "dataflow", label: "Data Flow", description: "Backend Data lens membership" },
  { id: "control", label: "Agent Control", description: "Planning, routing and agent control" },
  { id: "ingestion", label: "Ingestion & Indexing", description: "Load, parse, chunk and index" },
  { id: "retrieval", label: "Retrieval & Evidence", description: "Retrieval and evidence planes" },
  { id: "memory", label: "Memory & State", description: "Memory and persisted state" },
  { id: "governance", label: "Governance & Observability", description: "Guardrails, traces and evaluation" },
  { id: "runtime", label: "Runtime", description: "Runtime trace membership" },
  { id: "variants", label: "Variants", description: "Backend-declared architecture variants" },
  { id: "known", label: "Known Nodes", description: "Canonical reference capabilities" },
  { id: "extensions", label: "Extension Systems", description: "Optional extension subsystems" },
  { id: "unmapped", label: "Unmapped", description: "Explicitly unmapped components" },
  { id: "reasoning", label: "Reasoning Mode", description: "Deterministic, predefined or agentic mode" },
  { id: "topology", label: "Topology", description: "Deployment boundaries and endpoints" },
  { id: "source", label: "Source Map", description: "Backend Source lens membership" },
  { id: "risk", label: "Risk Lens", description: "Risk hints and assessment conflicts" },
];

function edgeIdsForNodes(graph: GraphViewModel, nodeIds: Set<string>): string[] {
  return graph.edges.filter((edge) => nodeIds.has(edge.from) || nodeIds.has(edge.to)).map((edge) => edge.id);
}

function viewFromNodeIds(
  graph: GraphViewModel,
  definition: ViewDefinition,
  nodeIds: Set<string>,
  supported: boolean,
  unavailableReason: string | null = null,
  extraEdgeIds: string[] = [],
): ArchitectureViewModel {
  return {
    ...definition,
    supported,
    unavailableReason,
    matchesNodeIds: [...nodeIds],
    matchesEdgeIds: [...new Set([...edgeIdsForNodes(graph, nodeIds), ...extraEdgeIds])],
  };
}

function lensView(graph: GraphViewModel, definition: ViewDefinition, lensId: string): ArchitectureViewModel {
  const lens = graph.filters.lenses.find((candidate) => candidate.id === lensId);
  if (!lens) {
    return viewFromNodeIds(
      graph,
      definition,
      new Set(),
      false,
      "The current build did not publish this lens.",
    );
  }
  return viewFromNodeIds(
    graph,
    definition,
    new Set(lens.matches_node_ids),
    lens.supported,
    lens.supported ? null : (lens.unavailable_reason ?? "No backend-provided membership."),
    lens.matches_edge_ids,
  );
}

function planeView(graph: GraphViewModel, definition: ViewDefinition, planeIds: string[]): ArchitectureViewModel {
  const nodeIds = new Set(
    graph.nodes.filter((node) => node.plane_id != null && planeIds.includes(node.plane_id)).map((node) => node.id),
  );
  const supported = graph.reference_map_version != null;
  return viewFromNodeIds(
    graph,
    definition,
    nodeIds,
    supported,
    supported ? null : "A backend reference-map projection is required.",
  );
}

export function buildArchitectureViews(graph: GraphViewModel): ArchitectureViewModel[] {
  const definitions = new Map(ARCHITECTURE_VIEW_DEFINITIONS.map((definition) => [definition.id, definition]));
  const definition = (id: ArchitectureViewId) => definitions.get(id)!;
  const overviewNodeIds = new Set(graph.nodes.map((node) => node.id));
  const hasReferenceProjection = graph.reference_map_version != null;

  const retrieval = planeView(graph, definition("retrieval"), ["retrieval", "evidence"]);
  const evidenceLens = graph.filters.lenses.find((lens) => lens.id === "lens:evidence");
  if (evidenceLens) {
    retrieval.matchesNodeIds = [...new Set([...retrieval.matchesNodeIds, ...evidenceLens.matches_node_ids])];
    retrieval.matchesEdgeIds = [...new Set([...retrieval.matchesEdgeIds, ...evidenceLens.matches_edge_ids])];
  }

  const explicitUnavailable = (id: ArchitectureViewId, reason: string): ArchitectureViewModel =>
    viewFromNodeIds(graph, definition(id), new Set(), false, reason);

  return [
    {
      ...definition("overview"),
      supported: true,
      unavailableReason: null,
      matchesNodeIds: [...overviewNodeIds],
      matchesEdgeIds: graph.edges.map((edge) => edge.id),
    },
    lensView(graph, definition("dataflow"), "lens:data"),
    lensView(graph, definition("control"), "lens:control"),
    planeView(graph, definition("ingestion"), ["ingestion_indexing"]),
    retrieval,
    planeView(graph, definition("memory"), ["memory_state"]),
    lensView(graph, definition("governance"), "lens:governance"),
    explicitUnavailable("runtime", "Runtime trace membership is not part of the current graph contract."),
    explicitUnavailable("variants", "Architecture variant metadata is not part of the current graph contract."),
    viewFromNodeIds(
      graph,
      definition("known"),
      new Set(graph.nodes.filter((node) => node.semantic_kind === "reference_capability").map((node) => node.id)),
      hasReferenceProjection,
      hasReferenceProjection ? null : "A backend reference-map projection is required.",
    ),
    planeView(graph, definition("extensions"), ["extension_subsystems"]),
    viewFromNodeIds(
      graph,
      definition("unmapped"),
      new Set(
        graph.nodes
          .filter(
            (node) =>
              node.semantic_kind === "unmapped_component" || node.related_unmapped_component_ids.length > 0,
          )
          .map((node) => node.id),
      ),
      hasReferenceProjection,
      hasReferenceProjection ? null : "A backend reference-map projection is required.",
    ),
    explicitUnavailable("reasoning", "Reasoning-mode metadata is not part of the current graph contract."),
    planeView(graph, definition("topology"), ["deployment_topology"]),
    lensView(graph, definition("source"), "lens:source"),
    lensView(graph, definition("risk"), "lens:risk"),
  ];
}
