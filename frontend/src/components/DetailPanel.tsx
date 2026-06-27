import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  FileCode2,
  Info,
  LoaderCircle,
  RefreshCw,
  Route,
  X,
} from "lucide-react";
import {
  detailScanResultSchema,
  type DataSourceMode,
  type DetailScanDepth,
  type DetailScanResult,
  type GraphEdgeModel,
  type GraphNodeModel,
  type GraphViewModel,
  type Selection,
  type TraceEvent,
  type ViewerPayload,
} from "../types";
import {
  targetForEdge,
  targetForEvidence,
  targetForNode,
  targetForTrace,
  type DetailScanTarget,
} from "../services/detailScanApi";
import { compactId, formatValue, titleCase } from "../utils/format";

type DetailMode = "overview" | "component" | "code_path";

type DetailRequestState = {
  projectId?: string;
  target?: DetailScanTarget;
  scanDepth?: DetailScanDepth;
  result?: DetailScanResult;
  isPending: boolean;
  error?: string;
  refreshWarning?: string;
};

type Props = {
  graph: GraphViewModel;
  payload: ViewerPayload;
  selected: Selection;
  traceEvents: TraceEvent[];
  dataSourceMode: DataSourceMode;
  projectId?: string;
  detailMode: DetailMode;
  detailRequest: DetailRequestState;
  onRunDetailScan: (target: DetailScanTarget, scanDepth: DetailScanDepth) => void;
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

function availableResults(payload: ViewerPayload): DetailScanResult[] {
  const canonical = payload.viewer_load_result.ai_system_map.detail_scans ?? [];
  const sample = detailScanResultSchema.safeParse(payload.detail_scan_result_sample);
  return sample.success ? [...canonical, sample.data] : canonical;
}

function latestMatchingResult(
  payload: ViewerPayload,
  target: DetailScanTarget | null,
  scanDepth: DetailScanDepth,
  requestResult?: DetailScanResult,
  alternativeTargets: DetailScanTarget[] = [],
) {
  if (!target) return undefined;
  const acceptedTargets = [target, ...alternativeTargets];
  const candidates = [
    ...availableResults(payload),
    ...(requestResult ? [requestResult] : []),
  ].filter(
    (result) =>
      result.scan_depth === scanDepth &&
      acceptedTargets.some(
        (candidate) =>
          result.target_type === candidate.targetType &&
          result.target === candidate.target,
      ),
  );
  return candidates.at(-1);
}

function RequestNotice({
  mode,
  projectId,
  target,
  scanDepth,
  request,
  hasResult,
}: {
  mode: DataSourceMode;
  projectId?: string;
  target: DetailScanTarget | null;
  scanDepth: DetailScanDepth;
  request: DetailRequestState;
  hasResult: boolean;
}) {
  if (mode === "sample") {
    return (
      <div className="detail-state is-sample">
        <Info size={14} />
        Sample mode is read-only. Switch to API mode and scan a project to request fresh detail results.
      </div>
    );
  }

  const isThisRequest =
    request.target?.targetType === target?.targetType &&
    request.target?.target === target?.target &&
    request.scanDepth === scanDepth;

  if (!projectId) {
    return (
      <div className="detail-state is-warning">
        <AlertTriangle size={14} />
        Import and scan a project in API mode first. Detail Scan requires the project session created by the main scan.
      </div>
    );
  }

  if (!target) {
    return (
      <div className="detail-state is-warning">
        <AlertTriangle size={14} />
        This item does not expose a valid backend Detail Scan target, so no request was sent.
      </div>
    );
  }

  if (isThisRequest && request.isPending) {
    return (
      <div className="detail-state is-loading" role="status">
        <LoaderCircle className="spin" size={14} />
        Running bounded {scanDepth === "component" ? "L2 component" : "L3 code-path"} scan…
      </div>
    );
  }

  if (isThisRequest && request.error) {
    return (
      <div className="detail-state is-error" role="alert">
        <AlertTriangle size={14} />
        <span>{request.error}</span>
      </div>
    );
  }

  if (isThisRequest && request.refreshWarning) {
    return (
      <div className="detail-state is-warning">
        <AlertTriangle size={14} />
        <span>{request.refreshWarning}</span>
      </div>
    );
  }

  if (!hasResult) {
    return (
      <div className="detail-empty-note">
        <Info className="ico" size={14} />
        No {scanDepth === "component" ? "component-level" : "code-path"} result exists for this target yet.
      </div>
    );
  }

  return null;
}

function DetailResultView({
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
  const isEmpty =
    result.findings.length === 0 &&
    (scanDepth === "component" || result.code_path.length === 0);

  return (
    <>
      <div className="detail-block">
        <span className="eyebrow">Result</span>
        <KeyValue label="status" value={result.status} tag />
        <KeyValue label="target" value={compactId(result.target)} />
        <KeyValue label="scope" value={result.target_type} tag />
        <KeyValue label="scan depth" value={result.scan_depth} tag />
        <KeyValue label="best effort" value={result.best_effort} tag />
      </div>

      {isEmpty ? (
        <div className="detail-state is-empty">
          <CheckCircle2 size={14} />
          The bounded scan completed without additional findings for this target.
        </div>
      ) : null}

      {result.findings.length > 0 ? (
        <div className="detail-block">
          <span className="eyebrow">Findings · {result.findings.length}</span>
          {result.findings.map((finding, index) => (
            <article className="detail-finding" key={`${finding.kind}-${index}`}>
              <div className="detail-finding-head">
                <strong>{titleCase(finding.kind)}</strong>
                {finding.best_effort ? <span className="tag">best effort</span> : null}
              </div>
              <p>{finding.summary}</p>
              {finding.evidence_ids.length > 0 ? (
                <div className="detail-evidence-actions">
                  {finding.evidence_ids.map((evidenceId) => {
                    const evidence = graph.details.evidence_by_id[evidenceId];
                    return (
                      <button type="button" key={evidenceId} onClick={() => onEvidenceDrilldown(evidenceId)}>
                        <FileCode2 size={13} />
                        <span>{evidence?.file ?? evidence?.path ?? compactId(evidenceId)}</span>
                        <ChevronRight size={13} />
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {scanDepth === "code_path" ? (
        <div className="detail-block">
          <span className="eyebrow">Project-owned code path · {result.code_path.length}</span>
          {result.code_path.length > 0 ? (
            <ol className="code-path-list">
              {result.code_path.map((step, index) => {
                const lineRange =
                  step.line_start == null
                    ? undefined
                    : step.line_end != null && step.line_end !== step.line_start
                      ? `${step.line_start}–${step.line_end}`
                      : String(step.line_start);
                return (
                  <li key={`${step.file}-${step.symbol ?? ""}-${step.line_start ?? index}`}>
                    <span className="code-path-index">{index + 1}</span>
                    <div>
                      <strong>{step.symbol ?? "Project code"}</strong>
                      <span className="mono">
                        {step.file}
                        {lineRange ? `:${lineRange}` : ""}
                      </span>
                      {step.best_effort ? <em>Best-effort hop</em> : null}
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <div className="detail-empty-note">
              <Info className="ico" size={14} />
              No project-owned code-path hops were found inside the backend’s bounded context.
            </div>
          )}
        </div>
      ) : null}

      {result.warnings.length > 0 ? (
        <div className="detail-block">
          <span className="eyebrow">Boundaries & uncertainty</span>
          <ul className="detail-warning-list">
            {result.warnings.map((warning) => (
              <li key={warning}>{titleCase(warning)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {Object.keys(result.context_limits).length > 0 ? (
        <details className="context-limits">
          <summary>Backend context limits</summary>
          <dl>
            {Object.entries(result.context_limits).map(([key, value]) => (
              <div key={key}>
                <dt>{titleCase(key)}</dt>
                <dd>{formatValue(value)}</dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}
    </>
  );
}

export function DetailPanel({
  graph,
  payload,
  selected,
  traceEvents,
  dataSourceMode,
  projectId,
  detailMode,
  detailRequest,
  onRunDetailScan,
  onDetailModeChange,
  onClose,
}: Props) {
  const [evidenceTargetId, setEvidenceTargetId] = useState<string>();

  useEffect(() => {
    if (!selected) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, selected]);

  useEffect(() => {
    setEvidenceTargetId(undefined);
  }, [selected?.id, selected?.kind]);

  const resolved = useMemo(() => {
    if (!selected) return null;
    if (selected.kind === "trace") {
      const trace = traceEvents.find((event) => event.id === selected.id);
      return trace ? { kind: "trace" as const, item: trace, target: targetForTrace(trace) } : null;
    }
    if (selected.kind === "node") {
      const node = graph.nodes.find((item) => item.id === selected.id);
      return node ? { kind: "node" as const, item: node, target: targetForNode(node) } : null;
    }
    const edge = graph.edges.find((item) => item.id === selected.id);
    return edge ? { kind: "edge" as const, item: edge, target: targetForEdge(edge) } : null;
  }, [graph.edges, graph.nodes, selected, traceEvents]);

  if (!selected || !resolved) return null;

  const node = resolved.kind === "node" ? (resolved.item as GraphNodeModel) : null;
  const edge = resolved.kind === "edge" ? (resolved.item as GraphEdgeModel) : null;
  const trace = resolved.kind === "trace" ? (resolved.item as TraceEvent) : null;
  const title = node?.label ?? edge?.label ?? edge?.relationship ?? trace?.step_type ?? "Trace step";
  const sub = node?.source_id ?? edge?.source_id ?? trace?.id ?? selected.id;
  const evidenceIds = node?.evidence_ids ?? edge?.evidence_ids ?? (trace?.evidence_id ? [trace.evidence_id] : []);
  const riskIds = node?.risk_hint_ids ?? edge?.risk_hint_ids ?? [];
  const scanDepth: DetailScanDepth = detailMode === "code_path" ? "code_path" : "component";
  const scanTarget =
    detailMode === "code_path" && evidenceTargetId
      ? targetForEvidence(evidenceTargetId)
      : resolved.target;
  const requestMatches =
    detailRequest.projectId === projectId &&
    detailRequest.target?.targetType === scanTarget?.targetType &&
    detailRequest.target?.target === scanTarget?.target &&
    detailRequest.scanDepth === scanDepth;
  const result = latestMatchingResult(
    payload,
    scanTarget,
    scanDepth,
    requestMatches ? detailRequest.result : undefined,
    node?.slot
      ? [{ targetType: "component_slot", target: node.slot, label: node.label }]
      : [],
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
          <span className={`kind-tag ${resolved.kind}`}>{titleCase(resolved.kind)}</span>
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
            onClick={() => {
              if (mode !== "code_path") setEvidenceTargetId(undefined);
              onDetailModeChange(mode);
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {detailMode === "overview" ? (
        <div className="inspector-body">
          <div className="detail-block">
            {node ? (
              <>
                <KeyValue label="id" value={compactId(selected.id)} />
                <KeyValue label="status" value={node.status} tag />
                <KeyValue label="type" value={node.type} tag />
                <KeyValue label="slot" value={node.slot} tag />
              </>
            ) : edge ? (
              <>
                <KeyValue label="relationship" value={edge.relationship} tag />
                <KeyValue label="flow" value={edge.flow_id?.replace("flow:", "")} tag />
                <KeyValue label="from" value={compactId(edge.from)} />
                <KeyValue label="to" value={compactId(edge.to)} />
                <KeyValue label="status" value={edge.status} tag />
              </>
            ) : (
              <>
                <KeyValue label="step" value={trace?.step_type} tag />
                <KeyValue label="component" value={trace?.component_id ?? trace?.unmapped_component_id} />
                <KeyValue label="edge" value={trace?.edge_id} />
                <KeyValue label="latency" value={trace?.latency_ms == null ? undefined : `${trace.latency_ms} ms`} />
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
        <div className="inspector-body">
          <div className="detail-scan-heading">
            <div>
              <span className="eyebrow">{detailMode === "component" ? "L2 component detail" : "L3 code path"}</span>
              <strong>{scanTarget?.label ?? "Unavailable target"}</strong>
              {evidenceTargetId ? <span className="mono">Evidence: {compactId(evidenceTargetId)}</span> : null}
            </div>
            {dataSourceMode === "api" ? (
              <button
                className="btn primary"
                type="button"
                disabled={!projectId || !scanTarget || (requestMatches && detailRequest.isPending)}
                onClick={() => {
                  if (projectId && scanTarget) onRunDetailScan(scanTarget, scanDepth);
                }}
              >
                {requestMatches && detailRequest.isPending ? (
                  <LoaderCircle className="spin" size={14} />
                ) : result ? (
                  <RefreshCw size={14} />
                ) : (
                  <Route size={14} />
                )}
                {requestMatches && detailRequest.isPending ? "Scanning…" : result ? "Run again" : "Run scan"}
              </button>
            ) : null}
          </div>

          <RequestNotice
            mode={dataSourceMode}
            projectId={projectId}
            target={scanTarget}
            scanDepth={scanDepth}
            request={requestMatches ? detailRequest : { isPending: false }}
            hasResult={result != null}
          />

          {result ? (
            <DetailResultView
              graph={graph}
              result={result}
              scanDepth={scanDepth}
              onEvidenceDrilldown={(evidenceId) => {
                setEvidenceTargetId(evidenceId);
                onDetailModeChange("code_path");
              }}
            />
          ) : null}
        </div>
      )}
    </>
  );
}
