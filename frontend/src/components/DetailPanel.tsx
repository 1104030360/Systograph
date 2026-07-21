import { useEffect } from "react";
import { CheckCircle2, Clipboard, FileCode2, Info, Route, X } from "lucide-react";
import type { GraphEdgeModel, GraphNodeModel, GraphViewModel, Selection, ViewerPayload } from "../types";
import { PrototypeIcon } from "../icons/PrototypeIcon";
import { getPlanePrototypeIconKind } from "../icons/prototypeIconRegistry";
import { compactId, formatValue, titleCase } from "../utils/format";
import { planeLabel } from "../utils/planes";

type DetailMode = "overview" | "evidence" | "code_path";

type Props = {
  graph: GraphViewModel;
  payload: ViewerPayload;
  selected: Selection;
  detailMode: DetailMode;
  onDetailModeChange: (mode: DetailMode) => void;
  onClose: () => void;
};

function hasValue(value: unknown): boolean {
  if (value === undefined || value === null || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value as Record<string, unknown>).length > 0;
  return true;
}

function KeyValue({ label, value, tag }: { label: string; value: unknown; tag?: boolean }) {
  if (!hasValue(value)) return null;
  return (
    <div className="kv">
      <div className="k">{label}</div>
      <div className={tag ? "v tag" : "v"}>{formatValue(value)}</div>
    </div>
  );
}

function SummaryFact({ label, value, title }: { label: string; value: unknown; title?: string }) {
  if (!hasValue(value)) return null;
  return (
    <div className="detail-summary-fact">
      <span>{label}</span>
      <strong title={title}>{formatValue(value)}</strong>
    </div>
  );
}

function StateFact({ label, value }: { label: string; value: unknown }) {
  if (!hasValue(value)) return null;
  return (
    <div className="detail-state-fact">
      <span>{label}</span>
      <strong>{titleCase(formatValue(value))}</strong>
    </div>
  );
}

function IdentifierRow({ label, value }: { label: string; value: string }) {
  const copyValue = () => {
    if (!navigator.clipboard) return;
    void navigator.clipboard.writeText(value).catch(() => undefined);
  };

  return (
    <div className="detail-identifier-row">
      <span>{label}</span>
      <code>{value}</code>
      <button type="button" className="icon-btn" aria-label={`Copy ${label}`} title={`Copy ${label}`} onClick={copyValue}>
        <Clipboard size={12} />
      </button>
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

function CodeDetails({ payload, targetIds }: { payload: ViewerPayload; targetIds: string[] }) {
  const sample = payload.detail_scan_result_sample;
  const proposal = payload.mapping_proposal_result_sample;
  const sampleTarget = sample ? String(sample.target ?? sample.target_id ?? "") : "";
  const matchesTarget = sample != null && sampleTarget !== "" && targetIds.includes(sampleTarget);

  if (!matchesTarget) {
    return (
      <div className="inspector-body" role="tabpanel" id="inspector-panel-code_path" aria-labelledby="inspector-tab-code_path">
        <div className="detail-block">
          <span className="eyebrow">Code and component scan</span>
          <div className="detail-empty-note">
            <Info className="ico" size={14} />
            No component-level or code-path scan result is available for this target yet. Run a backend detail scan to
            populate this view.
          </div>
        </div>
      </div>
    );
  }

  const suggestedComponent = proposal?.suggested_component as { name?: string } | undefined;
  const userActions = Array.isArray(proposal?.user_actions) ? (proposal.user_actions as unknown[]) : [];

  return (
    <div className="inspector-body" role="tabpanel" id="inspector-panel-code_path" aria-labelledby="inspector-tab-code_path">
      <div className="detail-block">
        <span className="eyebrow">Code and component scan</span>
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
      <details className="detail-disclosure">
        <summary>Raw backend scan result</summary>
        <pre className="code-block">{formatValue(sample)}</pre>
      </details>
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
  const headerDescription = isNode ? (node?.description ?? node?.subtitle) : edge?.relationship;
  const evidenceIds = isNode ? (node?.evidence_ids ?? []) : (edge?.evidence_ids ?? []);
  const riskIds = isNode ? (node?.risk_hint_ids ?? []) : (edge?.risk_hint_ids ?? []);
  const targetIds = [
    selected.id,
    isNode ? node?.component_id : undefined,
    isNode ? node?.source_id : edge?.source_id,
  ].filter((value): value is string => typeof value === "string");
  const projectionRelationshipCount = graph.relationships.filter(
    (relationship) => relationship.source_node_id === selected.id || relationship.target_node_id === selected.id,
  ).length;
  const coverageGate =
    node?.not_detected_coverage_gate_passed == null
      ? undefined
      : node.not_detected_coverage_gate_passed
        ? "passed"
        : "not passed";
  const identifiers = isNode
    ? [
        ["Node ID", selected.id],
        ["Source ID", node?.source_id],
        ["Reference ID", node?.reference_node_id],
        ["Component ID", node?.component_id],
        ["Profile ID", node?.profile_id],
      ]
    : [
        ["Edge ID", selected.id],
        ["Source ID", edge?.source_id],
        ["From", edge?.from],
        ["To", edge?.to],
      ];
  const availableIdentifiers = identifiers.filter((entry): entry is [string, string] => typeof entry[1] === "string");

  const tabs: Array<[DetailMode, string]> = [
    ["overview", "Summary"],
    ["evidence", "Evidence"],
    ["code_path", "Code"],
  ];

  // Plane chip renders only when the backend published plane_id; no inference.
  const planeIconKind = getPlanePrototypeIconKind(node?.plane_id);

  return (
    <>
      <div className="inspector-head">
        <div className="inspector-kind">
          <span className={isNode ? "kind-tag node" : "kind-tag edge"}>{isNode ? "Node" : "Edge"}</span>
          {node?.plane_id ? (
            <span className="plane-chip" title="Backend-declared plane">
              {planeIconKind ? <PrototypeIcon kind={planeIconKind} size={13} /> : null}
              {planeLabel(node.plane_id)}
            </span>
          ) : null}
          <button className="icon-btn" type="button" onClick={onClose} title="Close" aria-label="Close detail">
            <X size={15} />
          </button>
        </div>
        <div className="inspector-title">{title}</div>
        {headerDescription ? <div className="inspector-description">{headerDescription}</div> : null}
      </div>

      <div className="detail-tabs" role="tablist" aria-label="Inspector detail sections">
        {tabs.map(([mode, label]) => (
          <button
            key={mode}
            id={`inspector-tab-${mode}`}
            className={detailMode === mode ? "detail-tab is-active" : "detail-tab"}
            type="button"
            role="tab"
            aria-selected={detailMode === mode}
            aria-controls={`inspector-panel-${mode}`}
            onClick={() => onDetailModeChange(mode)}
          >
            {label}
          </button>
        ))}
      </div>

      {detailMode === "overview" ? (
        <div className="inspector-body" role="tabpanel" id="inspector-panel-overview" aria-labelledby="inspector-tab-overview">
          <div className="detail-state-grid" aria-label="Assessment and activation state">
            <StateFact label="Assessment" value={isNode ? node?.status : edge?.status} />
            {isNode ? <StateFact label="Activation" value={node?.activation} /> : null}
          </div>

          <div className="detail-summary-grid">
            {isNode ? (
              <>
                <SummaryFact label="Type" value={node?.type} />
                <SummaryFact label="Slot" value={node?.slot} />
                <SummaryFact
                  label="Component"
                  value={node?.component_id ? compactId(node.component_id) : undefined}
                  title={node?.component_id ?? undefined}
                />
                <SummaryFact label="Relationships" value={projectionRelationshipCount || undefined} />
              </>
            ) : (
              <>
                <SummaryFact label="Relationship" value={edge?.relationship ? titleCase(edge.relationship) : undefined} />
                <SummaryFact label="Flow" value={edge?.flow_id?.replace("flow:", "")} />
                <SummaryFact label="From" value={edge?.from ? compactId(edge.from) : undefined} />
                <SummaryFact label="To" value={edge?.to ? compactId(edge.to) : undefined} />
              </>
            )}
          </div>

          <details className="detail-disclosure">
            <summary>Identifiers <span>{availableIdentifiers.length}</span></summary>
            <div className="detail-identifiers">
              {availableIdentifiers.map(([label, value]) => (
                <IdentifierRow key={label} label={label} value={value} />
              ))}
            </div>
          </details>
        </div>
      ) : detailMode === "evidence" ? (
        <div className="inspector-body" role="tabpanel" id="inspector-panel-evidence" aria-labelledby="inspector-tab-evidence">
          {isNode ? (
            <details className="detail-disclosure">
              <summary>Assessment details</summary>
              <div className="detail-disclosure-body">
                <KeyValue label="semantic kind" value={node?.semantic_kind ? titleCase(node.semantic_kind) : undefined} tag />
                <KeyValue label="assessment scope" value={node?.assessment_scope} />
                <KeyValue label="coverage gate" value={coverageGate} tag />
                <KeyValue label="implementation depth" value={node?.implementation_depth_level} />
                <KeyValue label="depth reason" value={node?.implementation_depth_reason} />
                <KeyValue label="evidence strength" value={node?.evidence_strength} tag />
                <KeyValue label="uncertainty" value={node?.uncertainty} />
                <KeyValue label="direct evidence" value={node?.direct_evidence_ids} />
                <KeyValue label="indirect evidence" value={node?.indirect_evidence_ids} />
                <KeyValue label="negative evidence" value={node?.explicit_negative_evidence_ids} />
                <KeyValue label="conflicts" value={node?.conflict_fields} />
                <KeyValue label="related components" value={node?.related_component_ids} />
              </div>
            </details>
          ) : null}

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

          {isNode && node?.recommended_next_checks.length ? (
            <div className="detail-block">
              <span className="eyebrow">Recommended checks</span>
              <ul className="detail-check-list">
                {node.recommended_next_checks.map((check) => <li key={check}>{check}</li>)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <CodeDetails payload={payload} targetIds={targetIds} />
      )}
    </>
  );
}
