import { Braces, ChevronRight, FileCode2, Route, Sparkles } from "lucide-react";
import type { GraphEdgeModel, GraphNodeModel, GraphViewModel, Selection, ViewerPayload } from "../types";
import { compactId, formatValue, titleCase } from "../utils/format";

type Props = {
  graph: GraphViewModel;
  payload: ViewerPayload;
  selected: Selection;
  detailMode: "overview" | "component" | "code_path";
  onDetailModeChange: (mode: Props["detailMode"]) => void;
};

function KeyValue({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null || value === "") return null;

  return (
    <div className="kv-row">
      <span>{label}</span>
      <strong>{formatValue(value)}</strong>
    </div>
  );
}

function EvidenceList({ graph, ids }: { graph: GraphViewModel; ids: string[] }) {
  if (ids.length === 0) {
    return <p className="muted">No evidence linked.</p>;
  }

  return (
    <div className="evidence-list">
      {ids.map((id) => {
        const evidence = graph.details.evidence_by_id[id];

        return (
          <div className="evidence-row" key={id}>
            <FileCode2 size={15} />
            <div>
              <strong>{String(evidence?.title ?? compactId(id))}</strong>
              <span>{String(evidence?.file ?? evidence?.path ?? id)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RiskList({ graph, ids }: { graph: GraphViewModel; ids: string[] }) {
  if (ids.length === 0) return null;

  return (
    <div className="risk-list">
      {ids.map((id) => {
        const risk = graph.details.risk_hints_by_id[id];

        return (
          <div className="risk-row" key={id}>
            <strong>{String(risk?.title ?? compactId(id))}</strong>
            <span>{String(risk?.severity ?? "review")}</span>
          </div>
        );
      })}
    </div>
  );
}

function ComponentDetails({ payload, mode }: { payload: ViewerPayload; mode: "component" | "code_path" }) {
  const sample = payload.detail_scan_result_sample;
  const proposal = payload.mapping_proposal_result_sample;

  return (
    <div className="drilldown-panel">
      <div className="section-label">{mode === "component" ? "L2 Component Detail" : "L3 Code Path"}</div>
      <div className="drilldown-line">
        <Route size={15} />
        <span>{String(sample?.target ?? sample?.target_id ?? "selected target")}</span>
      </div>
      <KeyValue label="scan depth" value={sample?.scan_depth ?? mode} />
      <KeyValue label="status" value={sample?.status ?? "ready_for_backend"} />
      <KeyValue label="proposal" value={proposal?.status ?? "pending_confirmation"} />
      <pre>{formatValue(sample)}</pre>
    </div>
  );
}

function EmptyPanel() {
  return (
    <aside className="detail-panel">
      <div className="empty-detail">
        <Sparkles size={21} />
        <h2>Select a node or edge</h2>
        <p>Inspector will show evidence, risks, and progressive scan output.</p>
      </div>
    </aside>
  );
}

export function DetailPanel({ graph, payload, selected, detailMode, onDetailModeChange }: Props) {
  if (!selected || selected.kind === "trace") {
    return <EmptyPanel />;
  }

  const selectedItem =
    selected.kind === "node"
      ? graph.nodes.find((node) => node.id === selected.id)
      : graph.edges.find((edge) => edge.id === selected.id);

  if (!selectedItem) {
    return <EmptyPanel />;
  }

  const isNode = selected.kind === "node";
  const node = isNode ? (selectedItem as GraphNodeModel) : null;
  const edge = !isNode ? (selectedItem as GraphEdgeModel) : null;
  const title = isNode ? node?.label : edge?.label ?? edge?.relationship ?? "Edge";
  const subtitle = isNode ? node?.subtitle ?? node?.slot : edge?.relationship;
  const evidenceIds = isNode ? node?.evidence_ids ?? [] : edge?.evidence_ids ?? [];
  const riskIds = isNode ? node?.risk_hint_ids ?? [] : edge?.risk_hint_ids ?? [];

  return (
    <aside className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="section-label">{isNode ? "Node" : "Edge"}</span>
          <h2>{title}</h2>
          <p>{subtitle ? titleCase(String(subtitle)) : compactId(selected.id)}</p>
        </div>
        <Braces size={19} />
      </div>

      <div className="segmented-control">
        <button className={detailMode === "overview" ? "is-active" : ""} onClick={() => onDetailModeChange("overview")} type="button">
          Overview
        </button>
        <button className={detailMode === "component" ? "is-active" : ""} onClick={() => onDetailModeChange("component")} type="button">
          L2
        </button>
        <button className={detailMode === "code_path" ? "is-active" : ""} onClick={() => onDetailModeChange("code_path")} type="button">
          L3
        </button>
      </div>

      {detailMode === "overview" ? (
        <>
          <section className="detail-section">
            <KeyValue label="id" value={compactId(selected.id)} />
            <KeyValue label="status" value={node?.status} />
            <KeyValue label="slot" value={node?.slot} />
            <KeyValue label="relationship" value={edge?.relationship} />
            <KeyValue label="flow" value={edge?.flow_id} />
          </section>

          <section className="detail-section">
            <div className="section-row">
              <div className="section-label">Evidence</div>
              <ChevronRight size={15} />
            </div>
            <EvidenceList graph={graph} ids={evidenceIds} />
          </section>

          <section className="detail-section">
            <div className="section-label">Risk Hints</div>
            <RiskList graph={graph} ids={riskIds} />
            {riskIds.length === 0 ? <p className="muted">No linked risk hint.</p> : null}
          </section>
        </>
      ) : (
        <ComponentDetails payload={payload} mode={detailMode} />
      )}
    </aside>
  );
}
