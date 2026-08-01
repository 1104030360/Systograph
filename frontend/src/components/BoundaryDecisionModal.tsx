import { useEffect } from "react";
import { AlertTriangle, Check, ShieldAlert, X } from "lucide-react";
import type { ScanBoundaryAction, ScanBoundaryDecision, ScanBoundaryProposal } from "../types";

type Props = {
  proposals: ScanBoundaryProposal[];
  decisions: Record<string, ScanBoundaryAction>;
  isSubmitting: boolean;
  error?: string;
  onDecisionChange: (proposalId: string, decision: ScanBoundaryAction) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function BoundaryDecisionModal({
  proposals,
  decisions,
  isSubmitting,
  error,
  onDecisionChange,
  onSubmit,
  onCancel,
}: Props) {
  const allDecided = proposals.every((proposal) => decisions[proposal.proposal_id]);

  // Escape cancels like the other modals, but never while a submit is running.
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !isSubmitting) onCancel();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSubmitting, onCancel]);

  return (
    <div className="modal-scrim" role="presentation">
      <section className="boundary-modal" role="dialog" aria-modal="true" aria-labelledby="boundary-title">
        <header className="boundary-header">
          <div>
            <span className="eyebrow">Scan boundary</span>
            <h2 id="boundary-title">Review files before this scan</h2>
          </div>
          <button className="icon-btn" type="button" onClick={onCancel} aria-label="Close boundary review">
            <X size={16} />
          </button>
        </header>

        <p className="boundary-copy">
          Systograph found files that may contain local-only or sensitive data. Choose whether each item should be scanned
          for this run only.
        </p>

        <div className="boundary-list">
          {proposals.map((proposal) => (
            <BoundaryItem
              key={proposal.proposal_id}
              proposal={proposal}
              value={decisions[proposal.proposal_id]}
              onChange={(decision) => onDecisionChange(proposal.proposal_id, decision)}
            />
          ))}
        </div>

        {error ? <div className="boundary-error">{error}</div> : null}

        <footer className="boundary-actions">
          <button className="btn" type="button" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </button>
          <button className="btn is-active" type="button" onClick={onSubmit} disabled={!allDecided || isSubmitting}>
            {isSubmitting ? "Continuing..." : "Continue scan"}
          </button>
        </footer>
      </section>
    </div>
  );
}

export function decisionsForBoundary(
  proposals: ScanBoundaryProposal[],
  decisions: Record<string, ScanBoundaryAction>,
): ScanBoundaryDecision[] {
  return proposals.map((proposal) => ({
    target_path: proposal.target.path,
    fingerprint: proposal.target.fingerprint,
    decision: decisions[proposal.proposal_id] ?? "skip_this_run",
  }));
}

function BoundaryItem({
  proposal,
  value,
  onChange,
}: {
  proposal: ScanBoundaryProposal;
  value?: ScanBoundaryAction;
  onChange: (decision: ScanBoundaryAction) => void;
}) {
  const evidence = proposal.evidence_packet;
  return (
    <article className="boundary-item">
      <div className="boundary-item-main">
        <ShieldAlert size={18} />
        <div>
          <h3>{proposal.target.path}</h3>
          <p>{proposal.target.reason}</p>
          <div className="boundary-meta">
            <span>{proposal.target.risk_type}</span>
            <span>{proposal.target.target_type}</span>
            {proposal.target.size_bytes ? <span>{proposal.target.size_bytes.toLocaleString()} bytes</span> : null}
          </div>
        </div>
      </div>

      {evidence.masked_evidence_values.length > 0 || evidence.rule_ids.length > 0 ? (
        <div className="boundary-evidence">
          {evidence.rule_ids.map((rule) => (
            <span key={rule}>{rule}</span>
          ))}
          {evidence.masked_evidence_values.slice(0, 3).map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      ) : null}

      <div className="boundary-choice" role="group" aria-label={`Decision for ${proposal.target.path}`}>
        <button
          className={value === "scan_this_run" ? "is-active" : ""}
          type="button"
          onClick={() => onChange("scan_this_run")}
        >
          <Check size={14} />
          Scan this run
        </button>
        <button
          className={value === "skip_this_run" ? "is-active" : ""}
          type="button"
          onClick={() => onChange("skip_this_run")}
        >
          <AlertTriangle size={14} />
          Skip this run
        </button>
      </div>
    </article>
  );
}
