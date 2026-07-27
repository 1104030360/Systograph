import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  CircleDashed,
  FileCode2,
  Inbox,
  RefreshCw,
  SkipForward,
  X,
} from "lucide-react";
import { CandidateCard } from "./CandidateCard";
import { EditForm } from "./EditForm";
import { PROPOSALS } from "../../data/scanTemplate.mock";
import { useMappingProposal } from "../../hooks/useMappingProposal";
import { useWording } from "../../wording";
import type {
  ManualMappingCreate,
  MappingCandidate,
  MappingProposal,
  ProposalDecision,
} from "../../types";

export type ProposalTarget = { unmapped_id: string; node_path: string; node_kind?: string };
export type ProposalScenario = "ok" | "fallback" | "error" | "empty";

type ReasonAction = "reject" | "skip";
type ResultKind = "accept" | "edit" | "reject" | "skip";

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
        {isReject ? "Reject reason" : "Reason"} <span>(optional)</span>
      </label>
      <textarea
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder={isReject ? "Why none of these fit…" : "Why you're leaving this for now…"}
      />
      <div className="mp-reason-actions">
        <button
          className={isReject ? "btn danger" : "btn"}
          type="button"
          disabled={busy}
          onClick={() => onConfirm(reason.trim() || undefined)}
        >
          {isReject ? <X size={14} /> : <SkipForward size={14} />}
          {isReject ? "Confirm reject" : "Skip for now"}
        </button>
        <button className="btn ghost" type="button" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ResultView({
  kind,
  node,
  buildId,
}: {
  kind: ResultKind;
  node: ProposalTarget;
  buildId?: string;
}) {
  const result = {
    accept: {
      title: "Confirmation applied",
      body: `${node.node_path} was saved as a durable decision and materialized in a new build.`,
    },
    edit: {
      title: "Edited mapping applied",
      body: `The edited mapping for ${node.node_path} was backend-validated and materialized in a new build.`,
    },
    reject: {
      title: "Suggestions rejected",
      body: `${node.node_path} remains unknown. The rejection was saved without changing the canonical map.`,
    },
    skip: {
      title: "Left for later",
      body: `${node.node_path} remains unknown. The skip decision was saved for later review.`,
    },
  }[kind];
  const rejected = kind === "reject" || kind === "skip";
  return (
    <div className={`mp-result${rejected ? " is-reject" : ""}`}>
      <div className="ico">{rejected ? <SkipForward size={22} /> : <CheckCircle2 size={22} />}</div>
      <h3>{result.title}</h3>
      <p>{result.body}</p>
      {buildId ? <span className="mono">New build: {buildId}</span> : null}
    </div>
  );
}

function ProposalFrame({
  node,
  onClose,
  children,
  status,
  footer,
}: {
  node: ProposalTarget;
  onClose: () => void;
  children: React.ReactNode;
  status?: React.ReactNode;
  footer: React.ReactNode;
}) {
  const w = useWording();
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      opener?.focus();
    };
  }, [onClose]);

  return (
    <div className="mp-scrim" onClick={onClose}>
      <div
        className="mp-sheet"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={w.modalTitle}
      >
        <div className="mp-head">
          <div className="mp-head-top">
            <span className="kind-tag unmapped"><CircleDashed size={12} /> {w.unmappedTag}</span>
            <h2>{w.modalTitle}</h2>
            <button ref={closeRef} className="icon-btn mp-x" type="button" onClick={onClose} aria-label="Close">
              <X size={15} />
            </button>
          </div>
          <div className="mp-summary">
            <div className="mp-summary-file">
              <span className="mp-summary-k">{w.unmappedNodeLabel}</span>
              <span className="mp-summary-v"><FileCode2 size={14} /><span className="path">{node.node_path}</span></span>
            </div>
            <p>Suggestions are evidence-backed review options, not detected canonical facts.</p>
          </div>
        </div>
        {status}
        <div className="mp-body">{children}</div>
        <div className="mp-foot">{footer}</div>
      </div>
    </div>
  );
}

function LoadingCandidates() {
  return (
    <>
      {[0, 1, 2].map((index) => (
        <div className="mp-sk-cand" key={index}>
          <div className="sk h" /><div className="sk" /><div className="sk s" />
        </div>
      ))}
    </>
  );
}

function ApiProposalModal({
  node,
  apiBaseUrl,
  projectId,
  buildId,
  onClose,
  onApplied,
}: {
  node: ProposalTarget;
  apiBaseUrl: string;
  projectId: string;
  buildId: string;
  onClose: () => void;
  onApplied?: (buildId: string) => void;
}) {
  const mapping = useMappingProposal(apiBaseUrl, projectId, buildId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [reasonAction, setReasonAction] = useState<ReasonAction | null>(null);

  useEffect(() => {
    mapping.load({ sourceUnmappedId: node.unmapped_id });
    // The modal instance owns one immutable project/build/target scope.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.unmapped_id, projectId, buildId]);

  useEffect(() => {
    setSelectedId(mapping.proposal?.candidates[0]?.candidate_id || null);
  }, [mapping.proposal]);

  useEffect(() => {
    if (mapping.appliedBuild) onApplied?.(mapping.appliedBuild.build_id);
  }, [mapping.appliedBuild, onApplied]);

  const proposal = mapping.proposal;
  const proposalNode = proposal?.source_path
    ? { ...node, node_path: proposal.source_path }
    : node;
  const busy = mapping.isDeciding || mapping.isApplying;
  const finalKind: ResultKind | null = mapping.appliedBuild
    ? mapping.decision?.proposal.status === "edited" ? "edit" : "accept"
    : mapping.decision?.proposal.status === "rejected" ? "reject"
      : mapping.decision?.proposal.status === "skipped" ? "skip" : null;

  function decide(request: ProposalDecision) {
    if (proposal) mapping.decide(proposal, request);
  }

  function submitEdit(edited: ManualMappingCreate) {
    decide({ decision: "edit", edited_mapping: edited });
  }

  function renderCandidate(candidate: MappingCandidate, index: number) {
    if (!proposal) return null;
    return (
      <div key={candidate.candidate_id || `${proposal.proposal_id}:${index}`}>
        <CandidateCard
          cand={candidate}
          index={index}
          busy={busy}
          evidencePacket={proposal.evidence_packet}
          selected={Boolean(candidate.candidate_id) && selectedId === candidate.candidate_id}
          onSelect={() => setSelectedId(candidate.candidate_id || null)}
          onAccept={() => candidate.candidate_id && decide({ decision: "accept", candidate_id: candidate.candidate_id })}
          onEditOpen={() => {
            setEditingId(editingId === candidate.candidate_id ? null : candidate.candidate_id);
            setReasonAction(null);
          }}
          onReject={() => {
            setReasonAction("reject");
            setEditingId(null);
          }}
          onSkip={() => decide({ decision: "skip_for_now" })}
        />
        {editingId && editingId === candidate.candidate_id ? (
          <div className="mp-cand" style={{ borderTop: 0 }}>
            <EditForm
              cand={candidate}
              node={proposalNode}
              projectId={projectId}
              availableSlots={proposal.evidence_packet.available_slots}
              busy={busy}
              onCancel={() => setEditingId(null)}
              onSubmit={submitEdit}
            />
          </div>
        ) : null}
      </div>
    );
  }

  const status = mapping.isLoading ? (
    <div className="mp-status"><span className="spinner" /> Loading project-level suggestions for the current build…</div>
  ) : proposal?.provider_error_reason ? (
    <div className="mp-status is-fallback"><AlertTriangle size={14} /> Provider unavailable; showing deterministic suggestions.</div>
  ) : mapping.isApplying ? (
    <div className="mp-status"><span className="spinner" /> Decision saved. Backend is creating a new build…</div>
  ) : null;

  return (
    <ProposalFrame
      node={proposalNode}
      onClose={onClose}
      status={status}
      footer={
        <>
          <span className={`mp-foot-msg${mapping.decisionError || mapping.applyError ? " is-error" : ""}`}>
            {busy ? <span className="spinner" /> : mapping.decision ? <Check size={13} /> : null}
            {busy ? "Saving durable decision…" : mapping.decision ? "Decision saved" : `Base build: ${mapping.effectiveBuildId}`}
          </span>
          <div className="mp-foot-actions">
            {proposal?.status === "pending_user_confirmation" && !finalKind ? (
              <button className="btn" type="button" disabled={busy} onClick={() => setReasonAction("skip")}>
                <SkipForward size={14} /> Skip for now
              </button>
            ) : null}
            <button className={finalKind ? "btn primary" : "btn"} type="button" disabled={busy} onClick={onClose}>
              {finalKind ? "Done" : "Close"}
            </button>
          </div>
        </>
      }
    >
      {mapping.isLoading ? <LoadingCandidates /> : null}

      {mapping.loadError ? (
        <div className="st-state">
          <div className="ico is-error"><AlertTriangle size={20} /></div>
          <h4>Couldn't load suggestions</h4>
          <p>{mapping.loadError}</p>
          <button className="btn" type="button" onClick={() => mapping.load({ sourceUnmappedId: node.unmapped_id })}>
            <RefreshCw size={14} /> Try again
          </button>
        </div>
      ) : null}

      {mapping.isConflicted ? (
        <div className="st-state">
          <div className="ico is-error"><AlertTriangle size={20} /></div>
          <h4>Proposal state conflicted</h4>
          <p>This proposal was already finalized in another view. Reload the latest build before continuing.</p>
          <button className="btn" type="button" onClick={() => mapping.reloadLatest()}>
            <RefreshCw size={14} /> Reload latest build
          </button>
        </div>
      ) : null}

      {!mapping.isLoading && !mapping.loadError && proposal?.status === "pending_user_confirmation" && proposal.candidates.length === 0 ? (
        <div className="st-state">
          <div className="ico"><Inbox size={20} /></div>
          <h4>No suggestions yet</h4>
          <p>The component remains unknown. Retry after collecting more evidence.</p>
          <button className="btn" type="button" onClick={() => mapping.load({ sourceUnmappedId: node.unmapped_id })}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      ) : null}

      {!finalKind && !mapping.isConflicted && proposal?.status === "pending_user_confirmation"
        ? proposal.candidates.map(renderCandidate)
        : null}

      {reasonAction && proposal?.status === "pending_user_confirmation" && !finalKind ? (
        <ReasonComposer
          action={reasonAction}
          busy={busy}
          onCancel={() => setReasonAction(null)}
          onConfirm={(reason) => {
            decide({ decision: reasonAction === "reject" ? "reject" : "skip_for_now", reason });
            setReasonAction(null);
          }}
        />
      ) : null}

      {mapping.decisionError ? (
        <div className="mp-status is-error"><AlertTriangle size={14} /> {mapping.decisionError}</div>
      ) : null}

      {mapping.isStaleBuild ? (
        <div className="st-state">
          <div className="ico is-error"><AlertTriangle size={20} /></div>
          <h4>Base build is stale</h4>
          <p>The decision is saved, but the backend refused to branch from an older build. Reload latest before applying it.</p>
          <button className="btn" type="button" disabled={mapping.isReloadingLatest} onClick={() => mapping.reloadLatest()}>
            <RefreshCw size={14} /> Reload latest build
          </button>
        </div>
      ) : mapping.applyError ? (
        <div className="st-state">
          <div className="ico is-error"><AlertTriangle size={20} /></div>
          <h4>Decision saved; build not created</h4>
          <p>{mapping.applyError}</p>
          <button className="btn" type="button" onClick={mapping.retryApply}><RefreshCw size={14} /> Retry apply</button>
        </div>
      ) : null}

      {mapping.reloadLatestError ? (
        <div className="mp-status is-error"><AlertTriangle size={14} /> {mapping.reloadLatestError}</div>
      ) : null}

      {mapping.pendingMappingId && !mapping.isApplying && !mapping.applyError && !mapping.appliedBuild ? (
        <div className="st-state">
          <h4>Latest build loaded</h4>
          <p>The durable decision is still pending. Apply it to the reloaded latest build when ready.</p>
          <button className="btn primary" type="button" onClick={mapping.retryApply}>Apply to latest build</button>
        </div>
      ) : null}

      {finalKind ? (
        <ResultView kind={finalKind} node={proposalNode} buildId={mapping.appliedBuild?.build_id} />
      ) : null}
    </ProposalFrame>
  );
}

function SampleProposalModal({
  node,
  scenario,
  onClose,
}: {
  node: ProposalTarget;
  scenario: ProposalScenario;
  onClose: () => void;
}) {
  const proposal = PROPOSALS[node.unmapped_id] ?? PROPOSALS["unmapped:user-profile"];
  const [result, setResult] = useState<ResultKind | null>(null);
  const visibleProposal: MappingProposal = scenario === "empty" ? { ...proposal, candidates: [] } : proposal;
  return (
    <ProposalFrame
      node={node}
      onClose={onClose}
      status={scenario === "fallback" ? <div className="mp-status is-fallback">Sample deterministic fallback</div> : undefined}
      footer={<><span className="mp-foot-msg">Sample data</span><div className="mp-foot-actions"><button className="btn" onClick={onClose}>Close</button></div></>}
    >
      {scenario === "error" ? <div className="st-state"><h4>Couldn't load suggestions</h4><p>Sample error state.</p></div> : null}
      {scenario !== "error" && !visibleProposal.candidates.length ? <div className="st-state"><h4>No suggestions yet</h4></div> : null}
      {!result && scenario !== "error" ? visibleProposal.candidates.map((candidate, index) => (
        <CandidateCard
          key={candidate.candidate_id || index}
          cand={candidate}
          index={index}
          selected={index === 0}
          busy={false}
          evidencePacket={visibleProposal.evidence_packet}
          onSelect={() => {}}
          onAccept={() => setResult("accept")}
          onEditOpen={() => {}}
          onReject={() => setResult("reject")}
          onSkip={() => setResult("skip")}
        />
      )) : null}
      {result ? <ResultView kind={result} node={node} /> : null}
    </ProposalFrame>
  );
}

export function ProposalModal({
  node,
  scenario = "ok",
  apiBaseUrl,
  projectId,
  buildId,
  onClose,
  onApplied,
}: {
  node: ProposalTarget;
  scenario?: ProposalScenario;
  apiBaseUrl?: string;
  projectId?: string;
  buildId?: string;
  onClose: () => void;
  onApplied?: (buildId: string) => void;
}) {
  if (apiBaseUrl && projectId && buildId) {
    return (
      <ApiProposalModal
        node={node}
        apiBaseUrl={apiBaseUrl}
        projectId={projectId}
        buildId={buildId}
        onClose={onClose}
        onApplied={onApplied}
      />
    );
  }
  return <SampleProposalModal node={node} scenario={scenario} onClose={onClose} />;
}
