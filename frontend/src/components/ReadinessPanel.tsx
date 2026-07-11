import { CircleSlash2, ClipboardCheck, X } from "lucide-react";
import { readinessReportSchema, type ReadinessFinding } from "../contracts/viewer";
import type { GraphViewModel } from "../types";
import { titleCase } from "../utils/format";
import { makeGraphIndexes } from "../utils/graph";

type Props = {
  /** Raw backend readiness report — parsed here so a missing or unsupported
      report renders a degraded explanation instead of fabricated findings. */
  report: Record<string, unknown> | null;
  graph: GraphViewModel;
  onSelectComponent: (nodeId: string) => void;
  onClose: () => void;
};

function StatusChip({ status }: { status: string }) {
  return <span className={`readiness-chip s-${status}`}>{titleCase(status)}</span>;
}

function FindingCard({
  finding,
  graph,
  onSelectComponent,
}: {
  finding: ReadinessFinding;
  graph: GraphViewModel;
  onSelectComponent: (nodeId: string) => void;
}) {
  const { nodeIdBySource } = makeGraphIndexes(graph);

  return (
    <article className="readiness-finding" aria-label={finding.title ?? finding.finding_id}>
      <header className="readiness-finding-head">
        <strong>{finding.title ?? titleCase(finding.finding_id.replace(/^finding:/, ""))}</strong>
        <span className={`readiness-severity sev-${finding.severity}`}>{finding.severity}</span>
      </header>
      <div className="readiness-finding-meta">
        <StatusChip status={finding.status} />
        <span className="readiness-category">{titleCase(finding.category)}</span>
      </div>
      {finding.description ? <p>{finding.description}</p> : null}
      {finding.evidence_gap ? <p className="readiness-gap">{finding.evidence_gap}</p> : null}

      {finding.affected_component_ids.length > 0 ? (
        <div className="readiness-refs">
          <span className="eyebrow">Affected components</span>
          <div className="readiness-ref-list">
            {finding.affected_component_ids.map((componentId) => {
              const nodeId = nodeIdBySource.get(componentId);
              return nodeId ? (
                <button
                  key={componentId}
                  className="readiness-ref"
                  type="button"
                  onClick={() => onSelectComponent(nodeId)}
                >
                  {componentId}
                </button>
              ) : (
                <span key={componentId} className="readiness-ref is-unresolved" title="Not present in this projection">
                  {componentId}
                </span>
              );
            })}
          </div>
        </div>
      ) : null}

      {finding.evidence_ids.length > 0 ? (
        <div className="readiness-refs">
          <span className="eyebrow">Evidence</span>
          <div className="readiness-ref-list">
            {finding.evidence_ids.map((evidenceId) => (
              <span key={evidenceId} className="readiness-ref" title={evidenceId}>
                {graph.details.evidence_by_id[evidenceId]?.title ?? evidenceId}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {finding.recommended_next_checks.length > 0 ? (
        <div className="readiness-refs">
          <span className="eyebrow">Recommended next checks</span>
          <ul className="readiness-checks">
            {finding.recommended_next_checks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {finding.limitations.length > 0 ? (
        <p className="readiness-limitations">{finding.limitations.join(" ")}</p>
      ) : null}
    </article>
  );
}

export function ReadinessPanel({ report, graph, onSelectComponent, onClose }: Props) {
  const parsed = report == null ? null : readinessReportSchema.safeParse(report);

  return (
    <aside className="readiness-drawer" aria-label="Readiness findings">
      <header className="readiness-head">
        <span className="kind-tag">
          <ClipboardCheck aria-hidden="true" size={12} />
          Readiness
        </span>
        {parsed?.success ? (
          <span className={`readiness-verdict v-${parsed.data.release_verdict}`}>
            {titleCase(parsed.data.release_verdict)}
          </span>
        ) : null}
        <button className="icon-btn" type="button" aria-label="Close readiness panel" onClick={onClose}>
          <X size={14} />
        </button>
      </header>

      {parsed == null ? (
        <div className="readiness-empty">
          <CircleSlash2 aria-hidden="true" size={16} />
          <p>This build does not include a readiness report. Base projection views remain trustworthy.</p>
        </div>
      ) : !parsed.success ? (
        <div className="readiness-empty">
          <CircleSlash2 aria-hidden="true" size={16} />
          <p>The readiness report uses a contract this viewer version does not support, so findings are not shown.</p>
        </div>
      ) : (
        <div className="readiness-body">
          <div className="readiness-summary">
            <StatusChip status={parsed.data.summary.status} />
            <span className="readiness-static-note">Static analysis · not runtime verified</span>
          </div>
          {parsed.data.findings.length === 0 ? (
            <p className="readiness-static-note">No findings for this build.</p>
          ) : (
            parsed.data.findings.map((finding) => (
              <FindingCard
                key={finding.finding_id}
                finding={finding}
                graph={graph}
                onSelectComponent={onSelectComponent}
              />
            ))
          )}
        </div>
      )}
    </aside>
  );
}
