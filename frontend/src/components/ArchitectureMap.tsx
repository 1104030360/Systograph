import { useState } from "react";
import { ArrowRight, Boxes, ChevronLeft, ChevronRight, Info } from "lucide-react";
import type { GraphNodeModel, GraphViewModel, Selection } from "../types";
import { PrototypeIcon } from "../icons/PrototypeIcon";
import { getPlanePrototypeIconKind } from "../icons/prototypeIconRegistry";
import { nodeStatusKey, nodeStatusLabel } from "../utils/assessment";
import type { ArchitectureViewId, ArchitectureViewModel } from "../utils/architectureViews";
import { PLANE_PRESENTATION_ORDER, hasBackendPlaneProjection, planeLabel } from "../utils/planes";
import { compactId, titleCase } from "../utils/format";
import type { TraceHighlight } from "../utils/trace";
import { ArchitectureEdgeOverlay, type ArchitectureConnection } from "./ArchitectureEdgeOverlay";

type Props = {
  graph: GraphViewModel;
  views: ArchitectureViewModel[];
  activeViewId: ArchitectureViewId;
  search: string;
  selected: Selection;
  traceHighlight?: TraceHighlight;
  onSelect: (selection: Selection) => void;
};

const PLANE_DESCRIPTIONS: Record<string, string> = {
  input_intent: "Understand requests, intent and session context.",
  control: "Plan, route, coordinate and approve work.",
  ingestion_indexing: "Load, parse, chunk, embed and index source material.",
  retrieval: "Retrieve candidate context from indexed or connected sources.",
  extension_subsystems: "Optional graph, multimodal and specialist subsystems.",
  evidence: "Check, rank, cite and package supporting evidence.",
  generation: "Compose answers, use tools and apply output safeguards.",
  memory_state: "Persist session, workflow and long-term state.",
  governance_observability: "Guard, trace, evaluate and monitor the system.",
  deployment_topology: "Describe clients, services, workers and tool boundaries.",
};

function searchableText(node: GraphNodeModel): string {
  return [
    node.label,
    node.subtitle,
    node.description,
    node.reference_node_id,
    node.component_id,
    node.type,
    node.semantic_kind,
    node.slot,
  ]
    .filter((value): value is string => typeof value === "string")
    .join(" ")
    .toLocaleLowerCase();
}

function ArchitectureNodeCard({
  node,
  selected,
  dimmed,
  traceHighlighted,
  onSelect,
}: {
  node: GraphNodeModel;
  selected: boolean;
  dimmed: boolean;
  traceHighlighted: boolean;
  onSelect: () => void;
}) {
  const status = nodeStatusKey(node);
  const badges = [...new Set([node.type, node.activation].filter((value): value is string => Boolean(value)))];
  return (
    <button
      className={[
        "dr-node-card",
        `s-${status}`,
        `k-${node.semantic_kind ?? "unknown"}`,
        selected ? "is-selected" : "",
        dimmed ? "is-dimmed" : "",
        traceHighlighted ? "is-trace-highlight" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      type="button"
      data-node-id={node.id}
      data-semantic-kind={node.semantic_kind ?? undefined}
      aria-label={`Node ${node.label}`}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <span className="dr-node-topline">
        <span className={`dr-status-dot s-${status}`} aria-hidden="true" />
        <span>{nodeStatusLabel(status)}</span>
        <span className="dr-node-kind">{node.semantic_kind ? titleCase(node.semantic_kind) : "Node"}</span>
      </span>
      <strong>{node.label}</strong>
      <span className="dr-node-description">{node.description ?? node.subtitle ?? node.reference_node_id ?? node.id}</span>
      {badges.length > 0 ? (
        <span className="dr-node-badges">
          {badges.slice(0, 2).map((badge) => (
            <span key={badge}>{badge}</span>
          ))}
        </span>
      ) : null}
    </button>
  );
}

export function ArchitectureMap({ graph, views, activeViewId, search, selected, traceHighlight, onSelect }: Props) {
  const [flowsOpen, setFlowsOpen] = useState(false);

  if (!hasBackendPlaneProjection(graph)) {
    return (
      <div className="dr-map-empty" role="note">
        <Boxes size={24} aria-hidden="true" />
        <h3>No 10-plane projection in this payload</h3>
        <p>
          The legacy sample does not contain Plan 06 reference-map metadata. Switch Source to API and scan a local
          project to render the normalized architecture.
        </p>
      </div>
    );
  }

  const activeView = views.find((view) => view.id === activeViewId) ?? views[0];
  const focusedNodeIds = new Set(activeView.matchesNodeIds);
  const focusedEdgeIds = new Set(activeView.matchesEdgeIds);
  const traceNodeIds = new Set(traceHighlight?.nodeIds ?? []);
  const traceEdgeIds = new Set(traceHighlight?.edgeIds ?? []);
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const nodeMatches = (node: GraphNodeModel) =>
    (activeViewId === "overview" || focusedNodeIds.has(node.id)) &&
    (normalizedSearch === "" || searchableText(node).includes(normalizedSearch));
  const nodesByPlane = new Map<string, GraphNodeModel[]>();
  graph.nodes.forEach((node) => {
    const planeId = node.plane_id ?? "__unassigned__";
    nodesByPlane.set(planeId, [...(nodesByPlane.get(planeId) ?? []), node]);
  });
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const searchMatches = (node: GraphNodeModel | undefined) =>
    normalizedSearch === "" || (node != null && searchableText(node).includes(normalizedSearch));
  const connections: ArchitectureConnection[] = [
    ...graph.edges.map((edge) => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      source: "declared-edge" as const,
      focused:
        (activeViewId === "overview" || focusedEdgeIds.has(edge.id)) &&
        (searchMatches(nodeById.get(edge.from)) || searchMatches(nodeById.get(edge.to))),
      selected: selected?.kind === "edge" && selected.id === edge.id,
      traceHighlighted: traceEdgeIds.has(edge.id),
    })),
    ...graph.relationships.map((relationship) => ({
      id: relationship.id,
      from: relationship.source_node_id,
      to: relationship.target_node_id,
      source: "projection-relationship" as const,
      focused:
        (activeViewId === "overview" ||
          (focusedNodeIds.has(relationship.source_node_id) && focusedNodeIds.has(relationship.target_node_id))) &&
        (searchMatches(nodeById.get(relationship.source_node_id)) ||
          searchMatches(nodeById.get(relationship.target_node_id))),
      selected: false,
      traceHighlighted: false,
    })),
  ];
  const visibleEdges = graph.edges.filter(
    (edge) => {
      const fromNode = nodeById.get(edge.from);
      const toNode = nodeById.get(edge.to);
      return (
        (activeViewId === "overview" || focusedEdgeIds.has(edge.id)) &&
        (normalizedSearch === "" ||
          (fromNode != null && nodeMatches(fromNode)) ||
          (toNode != null && nodeMatches(toNode)))
      );
    },
  );

  return (
    <div className="dr-architecture-map">
      <div className={flowsOpen ? "dr-flow-drawer is-open" : "dr-flow-drawer"}>
        <button
          className="dr-flow-drawer-toggle"
          type="button"
          aria-label={flowsOpen ? "Hide backend-declared flows" : "Show backend-declared flows"}
          aria-controls="backend-declared-flows-card"
          aria-expanded={flowsOpen}
          title={flowsOpen ? "Hide backend-declared flows" : "Show backend-declared flows"}
          onClick={() => setFlowsOpen((open) => !open)}
        >
          {flowsOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
        </button>

        {flowsOpen ? (
        <section
          id="backend-declared-flows-card"
          className="dr-declared-flows"
          aria-labelledby="declared-flows-title"
        >
          <div className="dr-flow-heading">
            <div>
              <span className="eyebrow">Current build</span>
              <h3 id="declared-flows-title">Backend-declared flows</h3>
            </div>
            <span>{visibleEdges.length} visible</span>
          </div>
          {visibleEdges.length > 0 ? (
            <div className="dr-flow-list">
              {visibleEdges.slice(0, 12).map((edge) => (
                <button
                  className={selected?.kind === "edge" && selected.id === edge.id ? "dr-flow is-selected" : "dr-flow"}
                  key={edge.id}
                  type="button"
                  aria-label={`Flow ${nodeById.get(edge.from)?.label ?? compactId(edge.from)} to ${nodeById.get(edge.to)?.label ?? compactId(edge.to)}`}
                  onClick={() => onSelect({ kind: "edge", id: edge.id })}
                >
                  <span>{nodeById.get(edge.from)?.label ?? compactId(edge.from)}</span>
                  <ArrowRight size={13} aria-hidden="true" />
                  <span>{nodeById.get(edge.to)?.label ?? compactId(edge.to)}</span>
                  <small>{edge.label ?? edge.relationship ?? edge.flow_id ?? "declared edge"}</small>
                </button>
              ))}
            </div>
          ) : (
            <p className="dr-flow-empty">No backend-declared edge matches this view.</p>
          )}
        </section>
        ) : null}
      </div>

      <div className="dr-map-scroll-content">
        <ArchitectureEdgeOverlay connections={connections}>
          {PLANE_PRESENTATION_ORDER.map((planeId, index) => {
          const nodes = nodesByPlane.get(planeId) ?? [];
          const focusedCount = nodes.filter(nodeMatches).length;
              const planeIconKind = getPlanePrototypeIconKind(planeId);
          return (
            <section className={`dr-plane dr-plane-${planeId}`} key={planeId} data-plane-id={planeId}>
              <header className="dr-plane-heading">
                <span className="dr-plane-index">{String(index + 1).padStart(2, "0")}</span>
                <span className="dr-plane-icon" aria-hidden="true">
                  {planeIconKind ? <PrototypeIcon kind={planeIconKind} size={18} /> : null}
                </span>
                <span>
                  <strong>{planeLabel(planeId)}</strong>
                  <small>{PLANE_DESCRIPTIONS[planeId]}</small>
                </span>
                <span className="dr-plane-count">
                  {focusedCount === nodes.length ? nodes.length : `${focusedCount}/${nodes.length}`} nodes
                </span>
              </header>
              <div className="dr-plane-nodes">
                {nodes.length > 0 ? (
                  nodes.map((node) => (
                    <ArchitectureNodeCard
                      key={node.id}
                      node={node}
                      selected={selected?.kind === "node" && selected.id === node.id}
                      dimmed={!nodeMatches(node)}
                      traceHighlighted={traceNodeIds.has(node.id)}
                      onSelect={() => onSelect({ kind: "node", id: node.id })}
                    />
                  ))
                ) : (
                  <span className="dr-plane-empty">No backend node published in this plane.</span>
                )}
              </div>
            </section>
          );
          })}

          {(nodesByPlane.get("__unassigned__")?.length ?? 0) > 0 ? (
            <section className="dr-plane dr-plane-unassigned" data-plane-id="__unassigned__">
            <header className="dr-plane-heading">
              <span className="dr-plane-index">—</span>
              <span className="dr-plane-icon" aria-hidden="true">
                <Info size={17} />
              </span>
              <span>
                <strong>Unassigned components</strong>
                <small>The backend did not publish plane membership for these nodes.</small>
              </span>
              <span className="dr-plane-count">{nodesByPlane.get("__unassigned__")?.length ?? 0} nodes</span>
            </header>
            <div className="dr-plane-nodes">
              {(nodesByPlane.get("__unassigned__") ?? []).map((node) => (
                <ArchitectureNodeCard
                  key={node.id}
                  node={node}
                  selected={selected?.kind === "node" && selected.id === node.id}
                  dimmed={!nodeMatches(node)}
                  traceHighlighted={traceNodeIds.has(node.id)}
                  onSelect={() => onSelect({ kind: "node", id: node.id })}
                />
              ))}
            </div>
            </section>
          ) : null}
        </ArchitectureEdgeOverlay>
      </div>

    </div>
  );
}
