import { useState } from "react";
import { Check, Pencil } from "lucide-react";
import { COMPONENT_KINDS, PROJECT, SLOT_OPTIONS } from "../../data/scanTemplate.mock";
import type { ManualMappingCreate, MappingCandidate } from "../../types";

type NodeTarget = { unmapped_id: string; node_path: string; node_kind?: string };

export function EditForm({
  cand,
  node,
  busy,
  onCancel,
  onSubmit,
}: {
  cand: MappingCandidate;
  node: NodeTarget;
  busy: boolean;
  onCancel: () => void;
  onSubmit: (edited: ManualMappingCreate) => void;
}) {
  const isCapabilityCandidate = cand.candidate_type === "non_baseline_capability_candidate";
  const [form, setForm] = useState({
    target_slot: cand.target_slot ?? "",
    component_name: cand.component_name ?? cand.proposed_capability_candidate_name ?? cand.label ?? "",
    component_kind: cand.component_kind ?? cand.proposed_capability_candidate_kind ?? "other",
    reason: "",
  });
  const [errors, setErrors] = useState<{ target_slot?: string; component_name?: string }>({});
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  function submit() {
    const e: typeof errors = {};
    if (!form.component_name.trim()) e.component_name = "Component name is required.";
    if (!isCapabilityCandidate && !form.target_slot) e.target_slot = "Pick a target slot.";
    setErrors(e);
    if (Object.keys(e).length) return;
    onSubmit({
      project_id: PROJECT.project_id,
      mapping_type: isCapabilityCandidate ? "non_baseline_capability_candidate" : "existing_slot_mapping",
      decision: "confirmed",
      source_unmapped_id: node.unmapped_id,
      evidence_ids: cand.evidence_ids,
      target_slot: isCapabilityCandidate ? null : form.target_slot,
      component_name: isCapabilityCandidate ? null : form.component_name.trim(),
      component_kind: isCapabilityCandidate ? null : form.component_kind,
      capability_candidate_id: isCapabilityCandidate ? cand.proposed_capability_candidate_id : null,
      capability_candidate_name: isCapabilityCandidate ? form.component_name.trim() : null,
      capability_candidate_kind: isCapabilityCandidate ? form.component_kind : null,
      reason: form.reason.trim() || undefined,
    });
  }

  return (
    <div className="mp-edit" onClick={(e) => e.stopPropagation()}>
      <div className="mp-edit-head">
        <Pencil size={13} /> Edit mapping before confirming
      </div>
      <div className="mp-field-row">
        {!isCapabilityCandidate ? (
          <div className={"mp-field" + (errors.target_slot ? " has-error" : "")}>
            <label>Target slot</label>
            <select value={form.target_slot} onChange={(e) => set("target_slot", e.target.value)}>
              {SLOT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {errors.target_slot ? <span className="mp-err">{errors.target_slot}</span> : null}
          </div>
        ) : null}
        <div className="mp-field">
          <label>Component kind</label>
          <select value={form.component_kind} onChange={(e) => set("component_kind", e.target.value)}>
            {COMPONENT_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className={"mp-field" + (errors.component_name ? " has-error" : "")}>
        <label>Component name</label>
        <input
          value={form.component_name}
          onChange={(e) => set("component_name", e.target.value)}
          placeholder="e.g. UserAccountView"
        />
        {errors.component_name ? <span className="mp-err">{errors.component_name}</span> : null}
      </div>
      <div className="mp-field">
        <label>
          Reason{" "}
          <span style={{ textTransform: "none", color: "var(--text-faint)", fontWeight: 400 }}>(optional)</span>
        </label>
        <textarea
          value={form.reason}
          onChange={(e) => set("reason", e.target.value)}
          placeholder="Why this mapping is correct…"
        />
      </div>
      <div className="mp-edit-actions">
        <button className="btn primary" type="button" disabled={busy} onClick={submit}>
          <Check size={14} /> Submit edited mapping
        </button>
        <button className="btn ghost" type="button" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
