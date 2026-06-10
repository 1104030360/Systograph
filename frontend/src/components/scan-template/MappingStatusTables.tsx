import {
  ArrowRight,
  CheckCircle2,
  Inbox,
  RotateCcw,
  SkipForward,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { EvidenceList } from "../ui/EvidenceList";
import { SourceTag } from "../ui/SourceTag";
import { relTime } from "../../utils/time";
import { useWording } from "../../wording";
import type { ConfirmedMappingRow, PendingProposalRow, SkippedDecisionRow } from "../../types";

function EmptyRow({ Icon, title, body }: { Icon: LucideIcon; title: string; body: string }) {
  return (
    <div className="st-state">
      <div className="ico">
        <Icon size={20} />
      </div>
      <h4>{title}</h4>
      <p>{body}</p>
    </div>
  );
}

export function ConfirmedTable({ rows }: { rows: ConfirmedMappingRow[] }) {
  const w = useWording();
  if (!rows.length)
    return (
      <EmptyRow
        Icon={Inbox}
        title="Nothing confirmed yet"
        body="Matches you confirm or accept from suggestions show up here."
      />
    );
  return (
    <table className="st-table">
      <thead>
        <tr>
          <th>{w.colDetectedNode}</th>
          <th>{w.colMappedTo}</th>
          <th>{w.colSource}</th>
          <th>{w.colEvidence}</th>
          <th>Last updated</th>
          <th className="col-shrink"></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.mapping_id}>
            <td>
              <div className="cell-node">
                <span className="path">{r.node_path}</span>
                <span className="sub">{r.node_kind}</span>
              </div>
            </td>
            <td>
              <span className="cell-map">
                <ArrowRight size={13} className="arrow" />
                <span className="target">{r.target_label}</span>
              </span>
            </td>
            <td>
              <SourceTag source={r.source} />
            </td>
            <td>
              <EvidenceList items={r.evidence} compact />
            </td>
            <td className="reason mono" style={{ fontSize: 11 }}>
              {relTime(r.updated_at)}
            </td>
            <td className="cell-actions">
              <button className="btn" type="button">
                View
              </button>
              <button className="btn" type="button">
                Edit
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function PendingTable({
  rows,
  onReview,
}: {
  rows: PendingProposalRow[];
  onReview: (row: PendingProposalRow) => void;
}) {
  const w = useWording();
  if (!rows.length)
    return (
      <EmptyRow
        Icon={CheckCircle2}
        title="Nothing waiting for you"
        body="Every file Kai-Mind found has a match or a decision."
      />
    );
  return (
    <table className="st-table">
      <thead>
        <tr>
          <th>{w.unmappedNodeLabel}</th>
          <th>{w.colCandidates}</th>
          <th>{w.colBestCandidate}</th>
          <th>{w.colEvidence}</th>
          <th className="col-shrink"></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.unmapped_id}>
            <td>
              <div className="cell-node">
                <span className="path">{r.node_path}</span>
                <span className="sub">{r.node_kind}</span>
              </div>
            </td>
            <td>
              <span className="pill mono is-unmapped">
                <span className="dot" />
                {r.candidate_count} {w.candidateWord.toLowerCase()}s
              </span>
            </td>
            <td>
              <span className="cell-map">
                <span className="target">{r.best_candidate}</span>
              </span>
            </td>
            <td className="reason mono" style={{ fontSize: 11 }}>
              {r.evidence_count != null ? `${r.evidence_count} cited` : "—"}
            </td>
            <td className="cell-actions">
              <button className="btn primary" type="button" onClick={() => onReview(r)}>
                <Sparkles size={13} /> {w.reviewProposal}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SkippedTable({ rows }: { rows: SkippedDecisionRow[] }) {
  if (!rows.length)
    return (
      <EmptyRow
        Icon={SkipForward}
        title="Nothing skipped"
        body="Files you decide on later are parked here so you can come back to them."
      />
    );
  return (
    <table className="st-table">
      <thead>
        <tr>
          <th>Node</th>
          <th>Reason</th>
          <th>Skipped at</th>
          <th className="col-shrink"></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.decision_id}>
            <td>
              <div className="cell-node">
                <span className="path">{r.node_path}</span>
                <span className="sub">{r.node_kind}</span>
              </div>
            </td>
            <td className="reason">{r.reason}</td>
            <td className="reason mono" style={{ fontSize: 11 }}>
              {relTime(r.skipped_at)}
            </td>
            <td className="cell-actions">
              <button className="btn" type="button">
                <RotateCcw size={13} /> Reopen
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SkeletonTable() {
  return (
    <div>
      {[0, 1, 2, 3].map((i) => (
        <div className="st-sk-row" key={i}>
          <div className="sk" />
          <div className="sk short" />
          <div className="sk short" />
          <div className="sk short" />
          <div className="sk short" />
          <div className="sk short" />
        </div>
      ))}
    </div>
  );
}
