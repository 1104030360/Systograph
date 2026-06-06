import { useEffect } from "react";
import { CheckCircle2, FileCode2, Info, Route, X } from "lucide-react";
import type { GraphEdgeModel, GraphNodeModel, GraphViewModel, Selection, ViewerPayload } from "../types";
import { compactId, formatValue, titleCase } from "../utils/format";

type DetailMode = "overview" | "component" | "code_path";

type Props = {
  graph: GraphViewModel;
  payload: ViewerPayload;
  selected: Selection;
  detailMode: DetailMode;
  onDetailModeChange: (mode: DetailMode) => void;
  onClose: () => void;
};

function KeyValue({ label, value, tag }: { label: string; value: unknown; tag?: boolean }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="kv">
      <div className="k">{label}</div>
      <div className={tag ? "v tag" : "v"}>{formatValue(value)}</div>
    </div>
  );
}

function EvidenceItem({ graph, id }: { graph: GraphViewModel; id: string }) {
  const evidence = graph.details.evidence_by_id[id];
  return (
    <div className="evidence-item">
      <span className="ico">
        <FileCode2 size={15} />
      </span>
      <div>
        <div className="et">{evidence?.title ?? compactId(id)}</div>
        <div className="ef">{evidence?.file ?? evidence?.path ?? id}</div>
        {evidence?.value ? <div className="ev">{evidence.value}</div> : null}
      </div>
    </div>
  );
}

function RiskItem({ graph, id }: { graph: GraphViewModel; id: string }) {
  const risk = graph.details.risk_hints_by_id[id];
  const severity = risk?.severity_hint ?? risk?.severity ?? "review";
  return (
    <div className="risk-item">
      <div className="rt">
        <span className="rtt">{risk?.title ?? compactId(id)}</span>
        <span className={`sev ${severity}`}>{severity}</span>
      </div>
      {risk?.rationale ? <div className="rr">{risk.rationale}</div> : null}
      {risk?.uncertainty ? <div className="ru">Uncertainty: {risk.uncertainty}</div> : null}
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
  const eyebrow = mode === "component" ? "L2 component detail" : "L3 code path";

  if (!matchesTarget) {
    return (
      <div className="inspector-body">
        <div className="detail-block">
          <span className="eyebrow">{eyebrow}</span>
          <div className="detail-empty-note">
            <Info className="ico" size={14} />
            No {mode === "component" ? "component-level" : "code-path"} scan result is available for this target yet. Run a
            backend detail scan to populate this view.
          </div>
        </div>
      </div>
    );
  }

  const suggestedComponent = proposal?.suggested_component as { name?: string } | undefined;
  const userActions = Array.isArray(proposal?.user_actions) ? (proposal?.user_actions as unknown[]) : [];

  return (
    <div className="inspector-body">
      <div className="detail-block">
        <span className="eyebrow">{eyebrow}</span>
        <KeyValue label="target" value={compactId(sampleTarget)} />
        <KeyValue label="scan depth" value={sample.scan_depth} tag />
        <KeyValue label="status" value={sample.status} tag />
      </div>
      {proposal ? (
        <div className="detail-block">
          <span className="eyebrow">Mapping proposal</span>
          <div className="proposal-banner">
            <div className="pb-head">
              <Route size={14} />
              {suggestedComponent?.name ?? "Proposed mapping"}
            </div>
            <div className="pb-status mono">{String(proposal.status ?? "pending_user_confirmation")}</div>
            <div className="proposal-actions">
              {userActions.map((action) => (
                <button key={String(action)} className={action === "accept" ? "btn primary" : "btn"} type="button">
                  {titleCase(String(action))}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}
      <div className="detail-block">
        <span className="eyebrow">Raw scan result</span>
        <pre className="code-block">{formatValue(sample)}</pre>
      </div>
    </div>
  );
}

export function DetailPanel({ graph, payload, selected, detailMode, onDetailModeChange, onClose }: Props) {
  const isOpen = selected != null && selected.kind !== "trace";

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!selected || selected.kind === "trace") return null;

  const isNode = selected.kind === "node";
  const selectedItem = isNode
    ? graph.nodes.find((node) => node.id === selected.id)
    : graph.edges.find((edge) => edge.id === selected.id);
  if (!selectedItem) return null;

  const node = isNode ? (selectedItem as GraphNodeModel) : null;
  const edge = !isNode ? (selectedItem as GraphEdgeModel) : null;
  const title = isNode ? node?.label : (edge?.label ?? edge?.relationship ?? "Edge");
  const sub = isNode ? node?.source_id : (edge?.source_id ?? edge?.id);
  const evidenceIds = isNode ? (node?.evidence_ids ?? []) : (edge?.evidence_ids ?? []);
  const riskIds = isNode ? (node?.risk_hint_ids ?? []) : (edge?.risk_hint_ids ?? []);
  const targetIds = [selected.id, isNode ? node?.source_id : edge?.source_id].filter(
    (value): value is string => typeof value === "string",
  );

  const tabs: Array<[DetailMode, string]> = [
    ["overview", "Overview"],
    ["component", "L2 Component"],
    ["code_path", "L3 Code Path"],
  ];

  return (
    <>
      <div className="inspector-head">
        <div className="inspector-kind">
          <span className={isNode ? "kind-tag node" : "kind-tag edge"}>{isNode ? "Node" : "Edge"}</span>
          <button className="icon-btn" type="button" onClick={onClose} title="Close" aria-label="Close detail">
            <X size={15} />
          </button>
        </div>
        <div className="inspector-title">{title}</div>
        <div className="inspector-sub">{sub}</div>
      </div>

      <div className="detail-tabs">
        {tabs.map(([mode, label]) => (
          <button
            key={mode}
            className={detailMode === mode ? "detail-tab is-active" : "detail-tab"}
            type="button"
            aria-pressed={detailMode === mode}
            onClick={() => onDetailModeChange(mode)}
          >
            {label}
          </button>
        ))}
      </div>

      {detailMode === "overview" ? (
        <div className="inspector-body">
          <div className="detail-block">
            {isNode ? (
              <>
                <KeyValue label="id" value={compactId(selected.id)} />
                <KeyValue label="status" value={node?.status} tag />
                <KeyValue label="type" value={node?.type} tag />
                <KeyValue label="slot" value={node?.slot} tag />
              </>
            ) : (
              <>
                <KeyValue label="relationship" value={edge?.relationship} tag />
                <KeyValue label="flow" value={edge?.flow_id?.replace("flow:", "")} tag />
                <KeyValue label="from" value={compactId(edge?.from ?? "")} />
                <KeyValue label="to" value={compactId(edge?.to ?? "")} />
                <KeyValue label="status" value={edge?.status} tag />
              </>
            )}
          </div>

          <div className="detail-block">
            <span className="eyebrow">Evidence · {evidenceIds.length}</span>
            {evidenceIds.length > 0 ? (
              evidenceIds.map((id) => <EvidenceItem key={id} graph={graph} id={id} />)
            ) : (
              <div className="detail-empty-note">
                <Info className="ico" size={14} />
                No evidence linked to this element.
              </div>
            )}
          </div>

          <div className="detail-block">
            <span className="eyebrow">Risk hints · {riskIds.length}</span>
            {riskIds.length > 0 ? (
              riskIds.map((id) => <RiskItem key={id} graph={graph} id={id} />)
            ) : (
              <div className="detail-empty-note">
                <CheckCircle2 className="ico" size={14} />
                No risk hints attached.
              </div>
            )}
          </div>
        </div>
      ) : (
        <ComponentDetails payload={payload} mode={detailMode} targetIds={targetIds} />
      )}
    </>
  );
}
