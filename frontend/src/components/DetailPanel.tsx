import { useEffect, useRef } from "react";
import { Braces, ChevronRight, FileCode2, Route, X } from "lucide-react";
import type { GraphEdgeModel, GraphNodeModel, GraphViewModel, Selection, ViewerPayload } from "../types";
import { compactId, formatValue, titleCase } from "../utils/format";

type Props = {
  graph: GraphViewModel;
  payload: ViewerPayload;
  selected: Selection;
  detailMode: "overview" | "component" | "code_path";
  onDetailModeChange: (mode: Props["detailMode"]) => void;
  onClose: () => void;
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

function ComponentDetails({
  payload,
  mode,
  targetIds,
}: {
  payload: ViewerPayload;
  mode: "component" | "code_path";
  targetIds: string[];
}) {
  const sample = payload.detail_scan_result_sample;
  const proposal = payload.mapping_proposal_result_sample;
  const sampleTarget = sample ? String(sample.target ?? sample.target_id ?? "") : "";
  const matchesTarget = sample != null && sampleTarget !== "" && targetIds.includes(sampleTarget);

  if (!matchesTarget) {
    return (
      <div className="drilldown-panel">
        <div className="section-label">{mode === "component" ? "L2 Component Detail" : "L3 Code Path"}</div>
        <p className="muted">
          No {mode === "component" ? "component-level" : "code-path"} scan result is available for this target yet. Run a
          backend detail scan to populate this view.
        </p>
      </div>
    );
  }

  return (
    <div className="drilldown-panel">
      <div className="section-label">{mode === "component" ? "L2 Component Detail" : "L3 Code Path"}</div>
      <div className="drilldown-line">
        <Route size={15} />
        <span>{sampleTarget}</span>
      </div>
      <KeyValue label="scan depth" value={sample.scan_depth} />
      <KeyValue label="status" value={sample.status} />
      <KeyValue label="proposal" value={proposal?.status} />
      <pre>{formatValue(sample)}</pre>
    </div>
  );
}

export function DetailPanel({ graph, payload, selected, detailMode, onDetailModeChange, onClose }: Props) {
  const dialogRef = useRef<HTMLElement>(null);
  const isOpen = selected != null && selected.kind !== "trace";

  useEffect(() => {
    if (isOpen) dialogRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!selected || selected.kind === "trace") {
    return null;
  }

  const selectedItem =
    selected.kind === "node"
      ? graph.nodes.find((node) => node.id === selected.id)
      : graph.edges.find((edge) => edge.id === selected.id);

  if (!selectedItem) {
    return null;
  }

  const isNode = selected.kind === "node";
  const node = isNode ? (selectedItem as GraphNodeModel) : null;
  const edge = !isNode ? (selectedItem as GraphEdgeModel) : null;
  const title = isNode ? node?.label : edge?.label ?? edge?.relationship ?? "Edge";
  const subtitle = isNode ? node?.subtitle ?? node?.slot : edge?.relationship;
  const evidenceIds = isNode ? node?.evidence_ids ?? [] : edge?.evidence_ids ?? [];
  const riskIds = isNode ? node?.risk_hint_ids ?? [] : edge?.risk_hint_ids ?? [];
  const targetIds = [selected.id, isNode ? node?.source_id : edge?.source_id].filter(
    (value): value is string => typeof value === "string",
  );

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        aria-labelledby="detail-modal-title"
        aria-modal="true"
        className="detail-modal"
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="detail-header">
          <div>
            <span className="section-label">{isNode ? "Node" : "Edge"}</span>
            <h2 id="detail-modal-title">{title}</h2>
            <p>{subtitle ? titleCase(String(subtitle)) : compactId(selected.id)}</p>
          </div>
          <div className="detail-actions">
            <Braces size={19} />
            <button aria-label="Close detail" className="icon-button" onClick={onClose} type="button">
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="segmented-control">
          <button
            className={detailMode === "overview" ? "is-active" : ""}
            aria-pressed={detailMode === "overview"}
            onClick={() => onDetailModeChange("overview")}
            type="button"
          >
            Overview
          </button>
          <button
            className={detailMode === "component" ? "is-active" : ""}
            aria-pressed={detailMode === "component"}
            onClick={() => onDetailModeChange("component")}
            type="button"
          >
            L2
          </button>
          <button
            className={detailMode === "code_path" ? "is-active" : ""}
            aria-pressed={detailMode === "code_path"}
            onClick={() => onDetailModeChange("code_path")}
            type="button"
          >
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
          <ComponentDetails payload={payload} mode={detailMode} targetIds={targetIds} />
        )}
      </section>
    </div>
  );
}
