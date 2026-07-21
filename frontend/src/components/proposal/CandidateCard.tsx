import { Check, Info, Pencil, X } from "lucide-react";
import { EvidenceList } from "../ui/EvidenceList";
import { useWording } from "../../wording";
import type { EvidenceRef, MappingCandidate, MappingEvidencePacket } from "../../types";

// Fall back to bare evidence ids if the backend didn't resolve readable refs.
function evidenceItems(cand: MappingCandidate, packet: MappingEvidencePacket): EvidenceRef[] {
  if (cand.evidence_refs.length) return cand.evidence_refs;
  return cand.evidence_ids.map((id) => {
    const packetIndex = packet.evidence_ids.indexOf(id);
    const maskedSummary =
      packet.masked_snippets[packetIndex] ?? packet.masked_evidence_values[packetIndex];
    return {
      evidence_id: id,
      file: packet.source_file ?? "Evidence",
      label: maskedSummary ?? id,
    };
  });
}

export function CandidateCard({
  cand,
  index,
  selected,
  busy,
  evidencePacket,
  onSelect,
  onAccept,
  onEditOpen,
  onReject,
  onSkip,
}: {
  cand: MappingCandidate;
  index: number;
  selected: boolean;
  busy: boolean;
  evidencePacket: MappingEvidencePacket;
  onSelect: () => void;
  onAccept: () => void;
  onEditOpen: () => void;
  onReject: () => void;
  onSkip: () => void;
}) {
  const w = useWording();
  const isRecommended = cand.recommendation_level === "recommended";
  const isMaterializable =
    cand.candidate_type === "existing_slot_mapping" ||
    cand.candidate_type === "non_baseline_capability_candidate";
  const candidateName = cand.component_name ?? cand.proposed_capability_candidate_name ?? cand.label ?? "Candidate";
  const isSkip = cand.candidate_type === "skip_for_now";
  const needsInformation = cand.candidate_type === "needs_more_information";
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
          {w.verdictPre} <b>{candidateName}</b>
          {w.verdictPost}
        </p>
        <p className="mp-why">
          <span className="mp-why-label">{w.whyLabel}: </span>
          {cand.rationale}
        </p>
        <EvidenceList items={evidenceItems(cand, evidencePacket)} />
        {cand.candidate_type === "non_baseline_capability_candidate" ? (
          <p className="mp-why">This confirms a capability signal, not a detected component on the canonical map.</p>
        ) : null}
        {needsInformation ? (
          <p className="mp-why">Keep this item unknown until the scanner has stronger evidence.</p>
        ) : null}
        {cand.uncertainty_reason ? (
          <div className="mp-uncert">
            <Info size={13} className="ico" /> {cand.uncertainty_reason}
          </div>
        ) : null}
      </div>
      <div className="mp-cand-actions" onClick={(e) => e.stopPropagation()}>
        {isMaterializable ? (
          <>
            <button className="btn primary" type="button" disabled={busy} onClick={onAccept}>
              <Check size={14} /> {w.acceptBtn}
            </button>
            <button className="btn" type="button" disabled={busy} onClick={onEditOpen}>
              <Pencil size={14} /> {w.editBtn}
            </button>
          </>
        ) : isSkip ? (
          <button className="btn" type="button" disabled={busy} onClick={onSkip}>
            Skip for now
          </button>
        ) : null}
        <span className="spacer" />
        <button className="btn danger" type="button" disabled={busy} onClick={onReject}>
          <X size={14} /> {w.rejectBtn}
        </button>
      </div>
    </div>
  );
}
