import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronRight, Clipboard, FileCode2, Info, LoaderCircle, RefreshCw, X } from "lucide-react";
import type {
  DetailScanDepth,
  DetailScanResult,
  GraphEdgeModel,
  GraphNodeModel,
  GraphViewModel,
  Selection,
  ViewerPayload,
} from "../types";
import { PrototypeIcon } from "../icons/PrototypeIcon";
import { getPlanePrototypeIconKind } from "../icons/prototypeIconRegistry";
import { useDetailScan } from "../hooks/useDetailScan";
import {
  targetForEdge,
  targetForEvidence,
  targetForNode,
  type DetailScanTarget,
} from "../services/detailScanApi";
import { useViewerStore } from "../store/viewerStore";
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

type DetailScanState = ReturnType<typeof useDetailScan>;

function requestMatches(
  detailScan: DetailScanState,
  target: DetailScanTarget | null,
  scanDepth: DetailScanDepth,
) {
  return (
    target != null &&
    detailScan.variables?.target.targetType === target.targetType &&
    detailScan.variables.target.target === target.target &&
    detailScan.variables.scanDepth === scanDepth
  );
}

function resultFor(
  detailScan: DetailScanState,
  target: DetailScanTarget | null,
  scanDepth: DetailScanDepth,
  projectId: string | null,
  buildId: string | null,
): DetailScanResult | null {
  if (!target || !projectId || !buildId) return null;

  // Only walk the child lineage proven by responses created in this hook.
  // An unrelated externally-created latest build therefore cannot inherit a
  // stale UI result merely because its target id happens to match.
  const lineageBuildIds = new Set<string>();
  let cursor: string | null = buildId;
  while (cursor && !lineageBuildIds.has(cursor)) {
    lineageBuildIds.add(cursor);
    const child = detailScan.results.find(
      (item) => item.response.project_id === projectId && item.response.build_id === cursor,
    );
    cursor = child?.response.source_build_id ?? null;
  }

  return (
    detailScan.results
      .filter(
        (item) =>
          item.response.project_id === projectId &&
          item.response.build_id != null &&
          lineageBuildIds.has(item.response.build_id) &&
          item.response.detail_scan.scan_depth === scanDepth &&
          item.response.detail_scan.target_type === target.targetType &&
          item.response.detail_scan.target === target.target,
      )
      .at(-1)?.response.detail_scan ?? null
  );
}

function DetailScanResultView({
  graph,
  result,
  scanDepth,
  onEvidenceDrilldown,
}: {
  graph: GraphViewModel;
  result: DetailScanResult;
  scanDepth: DetailScanDepth;
  onEvidenceDrilldown: (evidenceId: string) => void;
}) {
  const empty = result.findings.length === 0 && (scanDepth === "component" || result.code_path.length === 0);
  return (
    <>
      <div className="detail-block">
        <span className="eyebrow">Backend result</span>
        <KeyValue label="status" value={result.status} tag />
        <KeyValue label="target" value={compactId(result.target)} />
        <KeyValue label="target type" value={result.target_type} tag />
        <KeyValue label="best effort" value={result.best_effort} tag />
      </div>

      {result.status === "partial" ? (
        <div className="detail-empty-note" role="status">
          <AlertTriangle className="ico" size={14} />
          Backend returned a partial bounded result. The base graph remains available.
        </div>
      ) : null}
      {result.status === "completed" ? (
        <div className="detail-empty-note" role="status">
          <CheckCircle2 className="ico" size={14} />
          Detail Scan completed on immutable child build data.
        </div>
      ) : null}
      {empty ? (
        <div className="detail-empty-note" role="status">
          <CheckCircle2 className="ico" size={14} />
          Scan completed without additional bounded findings for this target.
        </div>
      ) : null}

      {scanDepth === "component" && result.findings.length > 0 ? (
        <div className="detail-block">
          <span className="eyebrow">L2 findings · {result.findings.length}</span>
          {result.findings.map((finding, index) => (
            <div className="risk-item" key={`${finding.kind}-${index}`}>
              <div className="rt">
                <span className="rtt">{titleCase(finding.kind)}</span>
                {finding.best_effort ? <span className="sev review">best effort</span> : null}
              </div>
              <div className="rr">{finding.summary}</div>
              {finding.evidence_ids.map((evidenceId) => {
                const evidence = graph.details.evidence_by_id[evidenceId];
                return (
                  <button
                    className="btn"
                    type="button"
                    key={evidenceId}
                    onClick={() => onEvidenceDrilldown(evidenceId)}
                  >
                    <FileCode2 size={13} />
                    {evidence?.file ?? evidence?.path ?? compactId(evidenceId)}
                    <ChevronRight size={13} />
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      ) : null}

      {scanDepth === "code_path" ? (
        <div className="detail-block">
          <span className="eyebrow">L3 project-owned path · {result.code_path.length}</span>
          <div className="detail-empty-note">
            <Info className="ico" size={14} />
            Static evidence suggests these bounded hops; this is not runtime traversal proof.
          </div>
          {result.code_path.map((step, index) => {
            const lineRange =
              step.line_start == null
                ? ""
                : step.line_end != null && step.line_end !== step.line_start
                  ? `:${step.line_start}–${step.line_end}`
                  : `:${step.line_start}`;
            return (
              <div className="evidence-item" key={`${step.file}-${step.symbol ?? ""}-${step.line_start ?? index}`}>
                <span className="ico"><FileCode2 size={15} /></span>
                <div>
                  <div className="et">{step.symbol ?? "Project code"}</div>
                  <div className="ef">{step.file}{lineRange}</div>
                  {step.best_effort ? <div className="ru">Best-effort static hint</div> : null}
                </div>
              </div>
            );
          })}
          <div className="detail-empty-note">
            <Info className="ico" size={14} />
            Paths are backend-validated project-relative POSIX paths on both Windows and macOS; drive, UNC, absolute,
            backslash and parent-traversal paths are rejected by the frontend contract.
          </div>
        </div>
      ) : null}

      {result.warnings.length > 0 ? (
        <div className="detail-block">
          <span className="eyebrow">Warnings & uncertainty</span>
          <ul className="detail-check-list">
            {result.warnings.map((warning) => <li key={warning}>{titleCase(warning)}</li>)}
          </ul>
        </div>
      ) : null}

      {Object.keys(result.context_limits).length > 0 ? (
        <details className="detail-disclosure">
          <summary>Backend context limits</summary>
          <div className="detail-disclosure-body">
            {Object.entries(result.context_limits).map(([key, value]) => (
              <KeyValue key={key} label={titleCase(key)} value={value} />
            ))}
          </div>
        </details>
      ) : null}
    </>
  );
}

function DetailScanSection({
  graph,
  mode,
  projectId,
  buildId,
  historical,
  target,
  scanDepth,
  detailScan,
  onReturnToCurrent,
  onEvidenceDrilldown,
}: {
  graph: GraphViewModel;
  mode: "sample" | "api";
  projectId: string | null;
  buildId: string | null;
  historical: boolean;
  target: DetailScanTarget | null;
  scanDepth: DetailScanDepth;
  detailScan: DetailScanState;
  onReturnToCurrent: () => void;
  onEvidenceDrilldown: (evidenceId: string) => void;
}) {
  const matches = requestMatches(detailScan, target, scanDepth);
  const result = resultFor(detailScan, target, scanDepth, projectId, buildId);
  const errorMatches = matches && detailScan.requestBuildId === buildId;
  const run = () => target && detailScan.run({ target, scanDepth });

  if (mode === "sample") {
    return <div className="detail-empty-note"><Info className="ico" size={14} />Sample mode is read-only.</div>;
  }
  if (historical) {
    return (
      <div className="detail-empty-note">
        <Info className="ico" size={14} />Historical builds are immutable. Return to the current build to run Detail Scan.
        <button className="btn" type="button" onClick={onReturnToCurrent}>View current build</button>
      </div>
    );
  }
  if (!projectId || !buildId) {
    return <div className="detail-empty-note"><AlertTriangle className="ico" size={14} />Import and scan a project first.</div>;
  }
  if (!target) {
    return (
      <div className="detail-empty-note">
        <AlertTriangle className="ico" size={14} />This projection does not publish a supported canonical Detail Scan target.
      </div>
    );
  }
  if (matches && detailScan.isPending) {
    return <div className="detail-empty-note" role="status"><LoaderCircle className="spinner" size={14} />Running bounded scan…</div>;
  }
  if (errorMatches && detailScan.isStaleBase) {
    return (
      <div className="detail-empty-note" role="alert">
        <AlertTriangle className="ico" size={14} />The displayed base is stale. Reload the current build before retrying.
        <button className="btn" type="button" onClick={() => void detailScan.refreshCurrentBuild()}><RefreshCw size={13} />Reload current build</button>
      </div>
    );
  }
  if (errorMatches && detailScan.error) {
    return (
      <div className="detail-empty-note" role="alert">
        <AlertTriangle className="ico" size={14} />{detailScan.error}
        <button className="btn" type="button" onClick={run}><RefreshCw size={13} />Retry</button>
      </div>
    );
  }

  return (
    <>
      {result ? (
        <DetailScanResultView graph={graph} result={result} scanDepth={scanDepth} onEvidenceDrilldown={onEvidenceDrilldown} />
      ) : (
        <div className="detail-empty-note"><Info className="ico" size={14} />No result exists for this target and depth yet.</div>
      )}
      {matches && detailScan.data?.hydrationWarning ? (
        <div className="detail-empty-note" role="status">
          <AlertTriangle className="ico" size={14} />{detailScan.data.hydrationWarning}
          <button className="btn" type="button" onClick={() => void detailScan.refreshCurrentBuild()}><RefreshCw size={13} />Reload child build</button>
        </div>
      ) : null}
      <button className="btn primary" type="button" onClick={run}>{result ? "Run again" : scanDepth === "component" ? "Run L2 Detail Scan" : "Run L3 Code Path"}</button>
    </>
  );
}

export function DetailPanel({ graph, payload, selected, detailMode, onDetailModeChange, onClose }: Props) {
  const { dataSourceMode, apiBaseUrl, activeBuildId, setActiveBuildId } = useViewerStore();
  const projectId = payload.viewer_load_result.project_id;
  const buildId = payload.viewer_load_result.build_id;
  const detailScan = useDetailScan({ apiBaseUrl, projectId, buildId });
  const [evidenceTargetId, setEvidenceTargetId] = useState<string | null>(null);
  const isOpen = selected != null && selected.kind !== "trace";

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => setEvidenceTargetId(null), [selected?.id, selected?.kind]);

  if (!selected || selected.kind === "trace") return null;

  const isNode = selected.kind === "node";
  const selectedItem = isNode
    ? graph.nodes.find((node) => node.id === selected.id)
    : graph.edges.find((edge) => edge.id === selected.id);
  if (!selectedItem) return null;

  const node = isNode ? (selectedItem as GraphNodeModel) : null;
  const edge = !isNode ? (selectedItem as GraphEdgeModel) : null;
  const baseDetailTarget = node ? targetForNode(node) : edge ? targetForEdge(edge) : null;
  const codePathTarget = evidenceTargetId ? targetForEvidence(evidenceTargetId) : baseDetailTarget;
  const title = isNode ? node?.label : (edge?.label ?? edge?.relationship ?? "Edge");
  const headerDescription = isNode ? (node?.description ?? node?.subtitle) : edge?.relationship;
  const evidenceIds = isNode ? (node?.evidence_ids ?? []) : (edge?.evidence_ids ?? []);
  const riskIds = isNode ? (node?.risk_hint_ids ?? []) : (edge?.risk_hint_ids ?? []);
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
    ["evidence", "L2 Detail"],
    ["code_path", "L3 Code Path"],
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
          <div className="detail-block">
            <span className="eyebrow">L2 component detail</span>
            <DetailScanSection
              graph={graph}
              mode={dataSourceMode}
              projectId={projectId}
              buildId={buildId}
              historical={activeBuildId != null}
              target={baseDetailTarget}
              scanDepth="component"
              detailScan={detailScan}
              onReturnToCurrent={() => setActiveBuildId(null)}
              onEvidenceDrilldown={(evidenceId) => {
                setEvidenceTargetId(evidenceId);
                onDetailModeChange("code_path");
              }}
            />
          </div>
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
        <div className="inspector-body" role="tabpanel" id="inspector-panel-code_path" aria-labelledby="inspector-tab-code_path">
          <div className="detail-block">
            <span className="eyebrow">L3 code-path drill-down</span>
            {evidenceTargetId ? <KeyValue label="selected evidence" value={compactId(evidenceTargetId)} /> : null}
            <DetailScanSection
              graph={graph}
              mode={dataSourceMode}
              projectId={projectId}
              buildId={buildId}
              historical={activeBuildId != null}
              target={codePathTarget}
              scanDepth="code_path"
              detailScan={detailScan}
              onReturnToCurrent={() => setActiveBuildId(null)}
              onEvidenceDrilldown={() => undefined}
            />
          </div>
        </div>
      )}
    </>
  );
}
