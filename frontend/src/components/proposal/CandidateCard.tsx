import { Check, Info, Pencil, X } from "lucide-react";
import { EvidenceList } from "../ui/EvidenceList";
import { useWording } from "../../wording";
import type { EvidenceRef, MappingCandidate } from "../../types";

// Fall back to bare evidence ids if the backend didn't resolve readable refs.
function evidenceItems(cand: MappingCandidate): EvidenceRef[] {
  if (cand.evidence_refs.length) return cand.evidence_refs;
  return cand.evidence_ids.map((id) => ({ evidence_id: id, file: id }));
}

export function CandidateCard({
  cand,
  index,
  selected,
  busy,
  onSelect,
  onAccept,
  onEditOpen,
  onReject,
}: {
  cand: MappingCandidate;
  index: number;
  selected: boolean;
  busy: boolean;
  onSelect: () => void;
  onAccept: () => void;
  onEditOpen: () => void;
  onReject: () => void;
}) {
  const w = useWording();
  const isRecommended = cand.recommendation_level === "recommended";
  return (
    <div
      className={"mp-cand" + (selected ? " is-selected" : "") + (isRecommended ? " is-recommended" : "")}
      onClick={onSelect}
    >
      <div className="mp-cand-head">
        {isRecommended ? (
          <span className="mp-cand-rec">{w.recommendedLabel}</span>
        ) : (
          <span className="mp-cand-idx">
            {w.candidateWord} {index + 1}
          </span>
        )}
      </div>
      <div className="mp-cand-body">
        <p className="mp-verdict">
          {w.verdictPre} <b>{cand.component_name}</b>
          {w.verdictPost}
        </p>
        <p className="mp-why">
          <span className="mp-why-label">{w.whyLabel}: </span>
          {cand.rationale}
        </p>
        <EvidenceList items={evidenceItems(cand)} />
        {cand.uncertainty_reason ? (
          <div className="mp-uncert">
            <Info size={13} className="ico" /> {cand.uncertainty_reason}
          </div>
        ) : null}
      </div>
      <div className="mp-cand-actions" onClick={(e) => e.stopPropagation()}>
        <button className="btn primary" type="button" disabled={busy} onClick={onAccept}>
          <Check size={14} /> {w.acceptBtn}
        </button>
        <button className="btn" type="button" disabled={busy} onClick={onEditOpen}>
          <Pencil size={14} /> {w.editBtn}
        </button>
        <span className="spacer" />
        <button className="btn danger" type="button" disabled={busy} onClick={onReject}>
          <X size={14} /> {w.rejectBtn}
        </button>
      </div>
    </div>
  );
}
