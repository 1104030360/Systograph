/* ProposalModal — centered sheet for AI mapping proposals (never a right sidebar).
   Drives the full decision state machine from the design brief:
     load → (loaded | provider fallback | provider error | no candidates)
     candidate → accept | edit(+validation) | reject(+reason) | skip(+reason)
     result → accept/edit/reject/skip success

   The proposal shapes already match the real /api/mapping-proposals contract, so
   the swap point is small: replace the `runLoad` / `decide` setTimeout stubs with
   the real create / decide mutations and forward `provider_name` /
   `provider_error_reason` into the `scenario`. On any decision success, the host
   should refetch the viewer payload and close.

   To avoid overwhelming the user, only the recommended candidate is expanded by
   default; the rest sit behind an "Other suggestions" toggle. */
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileCode2,
  GitBranch,
  Inbox,
  PlugZap,
  RefreshCw,
  SkipForward,
  X,
} from "lucide-react";
import { CandidateCard } from "./CandidateCard";
import { EditForm } from "./EditForm";
import { PROPOSALS } from "../../data/scanTemplate.mock";
import { useWording } from "../../wording";
import type { ManualMappingCreate, MappingCandidate } from "../../types";

export type ProposalTarget = { unmapped_id: string; node_path: string; node_kind?: string };
export type ProposalScenario = "ok" | "fallback" | "error" | "empty";

type Phase = "loading" | "loaded" | "error" | "empty" | "result";
type ReasonAction = "reject" | "skip";
type ResultKind = "accept" | "edit" | "reject" | "skip";
type Provider = { name: string; fallback: boolean };
type Foot = { kind: "ok" | "error"; msg: string };
type Result = { kind: ResultKind; detail?: string };

function ReasonComposer({
  action,
  busy,
  onCancel,
  onConfirm,
}: {
  action: ReasonAction;
  busy: boolean;
  onCancel: () => void;
  onConfirm: (reason?: string) => void;
}) {
  const [reason, setReason] = useState("");
  const isReject = action === "reject";
  return (
    <div className="mp-reason">
      <label>
        {isReject ? "Reject reason" : "Reason"}{" "}
        <span style={{ textTransform: "none", color: "var(--text-faint)", fontWeight: 400 }}>(optional)</span>
      </label>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder={isReject ? "Why none of these fit…" : "Why you're leaving this for now…"}
      />
      <div className="mp-reason-actions">
        <button
          className={isReject ? "btn danger" : "btn"}
          type="button"
          disabled={busy}
          onClick={() => onConfirm(reason.trim() || undefined)}
        >
          {isReject ? (
            <>
              <X size={14} /> Confirm reject
            </>
          ) : (
            <>
              <SkipForward size={14} /> Confirm
            </>
          )}
        </button>
        <button className="btn ghost" type="button" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ResultView({ result, node }: { result: Result; node: ProposalTarget }) {
  const map = {
    accept: {
      Icon: CheckCircle2,
      cls: "",
      title: "Match confirmed",
      body: `${node.node_path} is now matched. The viewer will refresh with the new evidence.`,
    },
    edit: {
      Icon: CheckCircle2,
      cls: "",
      title: "Edited match saved",
      body: `Your edited match for ${node.node_path} was confirmed and stored.`,
    },
    reject: {
      Icon: X,
      cls: "is-reject",
      title: "Suggestions rejected",
      body: `No match was created for ${node.node_path}. You can ask for new suggestions later.`,
    },
    skip: {
      Icon: SkipForward,
      cls: "is-reject",
      title: "Left for later",
      body: `${node.node_path} moved to skipped. Come back to it anytime from Scan Template.`,
    },
  }[result.kind];
  const { Icon } = map;
  return (
    <div className={"mp-result " + map.cls}>
      <div className="ico">
        <Icon size={22} />
      </div>
      <h3>{map.title}</h3>
      <p>{map.body}</p>
      {result.detail ? <span className="mono">{result.detail}</span> : null}
    </div>
  );
}

export function ProposalModal({
  node,
  scenario = "ok",
  onClose,
}: {
  node: ProposalTarget;
  scenario?: ProposalScenario;
  onClose: () => void;
}) {
  const w = useWording();
  const [phase, setPhase] = useState<Phase>("loading");
  const [provider, setProvider] = useState<Provider | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [reasonAction, setReasonAction] = useState<ReasonAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [foot, setFoot] = useState<Foot | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [showOthers, setShowOthers] = useState(false);

  const proposal = PROPOSALS[node.unmapped_id] ?? PROPOSALS["unmapped:user-profile"];
  const candidates: MappingCandidate[] = proposal.candidates;

  function runLoad(s: ProposalScenario) {
    setPhase("loading");
    setFoot(null);
    setEditingId(null);
    setReasonAction(null);
    setShowOthers(false);
    const t = setTimeout(() => {
      if (s === "error") {
        setPhase("error");
        setProvider({ name: "nvidia-nim", fallback: false });
      } else if (s === "empty") {
        setPhase("empty");
        setProvider({ name: "nvidia-nim", fallback: false });
      } else if (s === "fallback") {
        setPhase("loaded");
        setProvider({ name: "deterministic", fallback: true });
        setSelectedId(candidates[0].candidate_id);
        setFoot({ kind: "ok", msg: w.fallbackSuggestions });
      } else {
        setPhase("loaded");
        setProvider({ name: "nvidia-nim", fallback: false });
        setSelectedId(candidates[0].candidate_id);
        setFoot({ kind: "ok", msg: `${candidates.length} ${w.candidateWord.toLowerCase()}s ready` });
      }
    }, 650);
    return () => clearTimeout(t);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => runLoad(scenario), []);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  function decide(fn: () => void) {
    setBusy(true);
    setFoot({ kind: "ok", msg: "Saving…" });
    setTimeout(() => {
      setBusy(false);
      fn();
    }, 600);
  }
  const accept = (cand: MappingCandidate) =>
    decide(() => {
      setResult({ kind: "accept", detail: `manual_mapping:${cand.candidate_id} · slot=${cand.target_slot}` });
      setPhase("result");
    });
  const submitEdit = (edited: ManualMappingCreate) =>
    decide(() => {
      setResult({ kind: "edit", detail: `slot=${edited.target_slot} · ${edited.component_name}` });
      setPhase("result");
    });
  const confirmReason = (reason?: string) =>
    decide(() => {
      if (!reasonAction) return;
      setResult({ kind: reasonAction, detail: reason ? `reason: "${reason}"` : "no reason given" });
      setPhase("result");
    });

  function renderCandidate(cand: MappingCandidate, i: number) {
    return (
      <div key={cand.candidate_id}>
        <CandidateCard
          cand={cand}
          index={i}
          busy={busy}
          selected={selectedId === cand.candidate_id}
          onSelect={() => setSelectedId(cand.candidate_id)}
          onAccept={() => accept(cand)}
          onEditOpen={() => {
            setSelectedId(cand.candidate_id);
            setEditingId(editingId === cand.candidate_id ? null : cand.candidate_id);
            setReasonAction(null);
          }}
          onReject={() => {
            setReasonAction("reject");
            setEditingId(null);
          }}
        />
        {editingId === cand.candidate_id ? (
          <div style={{ marginTop: -1 }}>
            <div className="mp-cand" style={{ borderTop: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
              <EditForm
                cand={cand}
                node={node}
                busy={busy}
                onCancel={() => setEditingId(null)}
                onSubmit={submitEdit}
              />
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function StatusRow() {
    if (phase === "loading")
      return (
        <div className="mp-status">
          <span className="spinner" /> {w.lookingForSuggestions}
        </div>
      );
    if (phase === "error")
      return (
        <div className="mp-status is-error">
          <PlugZap size={14} className="mp-status-ico" /> {w.suggestionsUnavailable}
        </div>
      );
    if (provider && provider.fallback)
      return (
        <div className="mp-status is-fallback">
          <AlertTriangle size={14} className="mp-status-ico" /> {w.fallbackSuggestions}
        </div>
      );
    if (phase === "empty")
      return (
        <div className="mp-status is-ok">
          {w.noSuggestionsFound}
        </div>
      );
    return null;
  }

  const suggestionSummary =
    phase === "empty"
      ? w.noSuggestionSummary
      : w.suggestionsFoundSummary(candidates.length);

  return (
    <div className="mp-scrim" onClick={onClose}>
      <div className="mp-sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={w.modalTitle}>
        {/* header */}
        <div className="mp-head">
          <div className="mp-head-top">
            <span className="kind-tag unmapped">
              <GitBranch size={12} /> {w.unmappedTag}
            </span>
            <h2>{w.modalTitle}</h2>
            <button className="icon-btn mp-x" type="button" onClick={onClose} title="Close" aria-label="Close">
              <X size={15} />
            </button>
          </div>
          <div className="mp-summary">
            <div className="mp-summary-file">
              <span className="mp-summary-k">{w.unmappedNodeLabel}</span>
              <span className="mp-summary-v">
                <FileCode2 size={14} style={{ color: "var(--text-3)", flex: "none" }} />
                <span className="path">{node.node_path}</span>
              </span>
            </div>
            <p>{suggestionSummary}</p>
          </div>
        </div>

        {phase !== "result" ? <StatusRow /> : null}

        {/* body */}
        {phase === "result" && result ? (
          <ResultView result={result} node={node} />
        ) : (
          <div className="mp-body">
            {phase === "loading"
              ? [0, 1, 2].map((i) => (
                  <div className="mp-sk-cand" key={i}>
                    <div className="sk h" />
                    <div className="sk" />
                    <div className="sk s" />
                    <div className="sk s" />
                  </div>
                ))
              : null}

            {phase === "error" ? (
              <div className="st-state">
                <div className="ico is-error">
                  <PlugZap size={20} />
                </div>
                <h4>Couldn't get suggestions</h4>
                <p>Kai-Mind couldn't reach the suggestion service. Try again, or leave this file for later.</p>
                <button className="btn" type="button" onClick={() => runLoad("ok")}>
                  <RefreshCw size={14} /> Try again
                </button>
              </div>
            ) : null}

            {phase === "empty" ? (
              <div className="st-state">
                <div className="ico">
                  <Inbox size={20} />
                </div>
                <h4>No suggestions yet</h4>
                <p>
                  Kai-Mind didn't find a match for this file. Try a deeper scan first to gather more detail, then ask
                  again.
                </p>
                <button className="btn" type="button" onClick={() => runLoad("ok")}>
                  <RefreshCw size={14} /> Try again
                </button>
              </div>
            ) : null}

            {phase === "loaded" ? (
              <>
                {renderCandidate(candidates[0], 0)}
                {candidates.length > 1 ? (
                  <>
                    <button className="mp-more" type="button" onClick={() => setShowOthers((s) => !s)}>
                      {showOthers ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      {w.otherSuggestions(candidates.length - 1)}
                    </button>
                    {showOthers ? candidates.slice(1).map((cand, i) => renderCandidate(cand, i + 1)) : null}
                  </>
                ) : null}
              </>
            ) : null}

            {reasonAction ? (
              <ReasonComposer
                action={reasonAction}
                busy={busy}
                onCancel={() => setReasonAction(null)}
                onConfirm={confirmReason}
              />
            ) : null}
          </div>
        )}

        {/* footer */}
        {phase !== "result" ? (
          <div className="mp-foot">
            <span className={"mp-foot-msg" + (foot ? (foot.kind === "error" ? " is-error" : " is-ok") : "")}>
              {busy ? <span className="spinner" style={{ width: 13, height: 13, borderWidth: 2 }} /> : null}
              {foot ? foot.msg : "Reviewing"}
            </span>
            <div className="mp-foot-actions">
              {phase === "loaded" ? (
                <button
                  className="btn ghost"
                  type="button"
                  disabled={busy}
                  onClick={() => runLoad(provider && provider.fallback ? "fallback" : "ok")}
                >
                  <RefreshCw size={14} /> Regenerate
                </button>
              ) : null}
              <button
                className="btn"
                type="button"
                disabled={busy}
                onClick={() => {
                  setReasonAction("skip");
                  setEditingId(null);
                }}
              >
                <SkipForward size={14} /> {w.skipThisNode}
              </button>
              <button className="btn" type="button" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        ) : (
          <div className="mp-foot">
            <span className="mp-foot-msg is-ok">
              <Check size={13} /> Saved
            </span>
            <div className="mp-foot-actions">
              <button className="btn primary" type="button" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
