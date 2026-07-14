import { useEffect, useRef } from "react";
import { CircleSlash2, ClipboardCheck, X } from "lucide-react";
import { readinessReportSchema, type ReadinessFinding } from "../contracts/viewer";
import type { GraphViewModel } from "../types";
import { titleCase } from "../utils/format";

type Props = {
  /** Raw backend readiness report — parsed here so a missing or unsupported
      report renders a degraded explanation instead of fabricated findings. */
  report: Record<string, unknown> | null;
  graph: GraphViewModel;
  onClose: () => void;
};

function StatusChip({ status }: { status: string }) {
  return <span className={`readiness-chip s-${status}`}>{titleCase(status)}</span>;
}

function FindingCard({ finding, graph }: { finding: ReadinessFinding; graph: GraphViewModel }) {
  return (
    <article className="readiness-finding" aria-label={finding.title}>
      <header className="readiness-finding-head">
        <strong>{finding.title}</strong>
      </header>
      <div className="readiness-finding-meta">
        <StatusChip status={finding.status} />
        <span className="readiness-category">{titleCase(finding.category)}</span>
      </div>
      <p>{finding.reason}</p>

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
    </article>
  );
}

export function ReadinessPanel({ report, graph, onClose }: Props) {
  const parsed = report == null ? null : readinessReportSchema.safeParse(report);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      trigger?.focus();
    };
  }, [onClose]);

  return (
    <div
      className="modal-scrim"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="readiness-dialog" role="dialog" aria-modal="true" aria-labelledby="readiness-dialog-title">
        <header className="readiness-head">
          <div>
            <span className="eyebrow">Build assessment</span>
            <h2 id="readiness-dialog-title">
              <ClipboardCheck aria-hidden="true" size={17} />
              Readiness
            </h2>
          </div>
          {parsed?.success ? <StatusChip status={parsed.data.grounding.status} /> : null}
          <button
            ref={closeButtonRef}
            className="icon-btn"
            type="button"
            aria-label="Close readiness dialog"
            onClick={onClose}
          >
            <X size={15} />
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
              <span className="readiness-static-note">
                Grounding {titleCase(parsed.data.grounding.applicability)}
                {parsed.data.primary_map_type ? ` · ${titleCase(parsed.data.primary_map_type)}` : ""} · static analysis
              </span>
            </div>
            {parsed.data.grounding.reason ? (
              <p className="readiness-static-note">{parsed.data.grounding.reason}</p>
            ) : null}

            {parsed.data.findings.length === 0 ? (
              <p className="readiness-static-note">No findings for this build.</p>
            ) : (
              parsed.data.findings.map((finding) => (
                <FindingCard key={finding.finding_id} finding={finding} graph={graph} />
              ))
            )}

            {parsed.data.recommended_next_checks.length > 0 ? (
              <div className="readiness-refs">
                <span className="eyebrow">Report next checks</span>
                <ul className="readiness-checks">
                  {parsed.data.recommended_next_checks.map((check) => (
                    <li key={check}>{check}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {parsed.data.limitations.length > 0 ? (
              <p className="readiness-limitations">{parsed.data.limitations.join(" ")}</p>
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
