import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  FileSearch,
  FolderSearch,
  Info,
  LoaderCircle,
  RefreshCw,
  ShieldAlert,
  X,
} from "lucide-react";
import {
  decisionsForInventory,
  proposalIdentity,
  type InventoryDecisionSerialization,
  type ProjectScanFlowError,
  type ProjectScanFlowStatus,
} from "../hooks/useProjectScanFlow";
import type {
  InventoryBoundaryProposal,
  InventoryRequestedTargetView,
  ScanBoundaryAction,
  ScanInventoryPreflightResponse,
} from "../types";

type Props = {
  status: ProjectScanFlowStatus;
  preflight: ScanInventoryPreflightResponse | null;
  decisions: Record<string, ScanBoundaryAction>;
  requestedPaths: string[];
  missingRequiredCount: number;
  error: ProjectScanFlowError | null;
  notice: string | null;
  isBusy: boolean;
  onDecisionChange: (proposal: InventoryBoundaryProposal, decision: ScanBoundaryAction) => void;
  onCheckPath: (path: string) => void;
  onRemoveRequestedPath: (path: string) => void;
  onLoadMore: () => void;
  onRetryPreflight: () => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function BoundaryDecisionModal({
  status,
  preflight,
  decisions,
  requestedPaths,
  missingRequiredCount,
  error,
  notice,
  isBusy,
  onDecisionChange,
  onCheckPath,
  onRemoveRequestedPath,
  onLoadMore,
  onRetryPreflight,
  onSubmit,
  onCancel,
}: Props) {
  const dialogRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [pathInput, setPathInput] = useState("");

  // Initial focus and focus restore run once per dialog lifetime. Re-running
  // them on every status change would yank a keyboard user back to the title
  // after each path check, and the cleanup would move focus outside a dialog
  // that is still open.
  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    titleRef.current?.focus();
    return () => previouslyFocused?.focus();
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && status !== "submitting") {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      // The title holds initial focus but is tabindex="-1", so it is not in the
      // list above. Without this branch Shift+Tab from it — or from anywhere
      // focus has escaped to — would leave an aria-modal dialog.
      if (!focusable.includes(document.activeElement as HTMLElement)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onCancel, status]);

  const serialized = useMemo<InventoryDecisionSerialization>(
    () => (preflight ? decisionsForInventory(preflight, decisions) : { ok: true, decisions: [] }),
    [decisions, preflight],
  );
  const explicitDecisionCount = serialized.ok ? serialized.decisions.length : 0;

  function handlePathSubmit(event: FormEvent) {
    event.preventDefault();
    onCheckPath(pathInput);
  }

  const showBlockingState = status === "stale" || status === "baseline_error" || (status === "error" && !preflight);
  const hasReview = preflight != null && !showBlockingState;

  return (
    <div className="modal-scrim inventory-scrim" role="presentation">
      <section
        ref={dialogRef}
        className="boundary-modal inventory-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="boundary-title"
        aria-describedby="boundary-description"
        aria-busy={isBusy}
      >
        <header className="boundary-header inventory-header">
          <div>
            <span className="eyebrow">Inventory preflight</span>
            <h2 ref={titleRef} id="boundary-title" tabIndex={-1}>Review scan scope</h2>
          </div>
          <button
            className="icon-btn"
            type="button"
            onClick={onCancel}
            aria-label="Close inventory preflight"
            disabled={status === "submitting"}
          >
            <X size={16} />
          </button>
        </header>

        <p id="boundary-description" className="boundary-copy inventory-intro">
          Systograph prepared a recommended scope from backend policy and project ignore rules. Adjustments apply only
          to this scan; they do not change <code>.gitignore</code>, the inventory policy, or a saved preference.
        </p>

        {showBlockingState ? (
          <BlockingState
            status={status}
            error={error}
            onRetry={onRetryPreflight}
            onCancel={onCancel}
          />
        ) : !preflight ? (
          <div className="inventory-loading" role="status" aria-live="polite">
            <LoaderCircle className="spin" size={22} />
            <div>
              <strong>{status === "importing" ? "Importing project" : "Preparing inventory preflight"}</strong>
              <p>The backend is building a metadata-only candidate summary. No scan has started yet.</p>
            </div>
          </div>
        ) : hasReview ? (
          <>
            <div className="inventory-scroll">
              <InventoryIdentity preflight={preflight} />
              <InventorySummary preflight={preflight} />

              {notice ? (
                <div className="inventory-notice" role="status" aria-live="polite">
                  <Info size={16} />
                  <span>{notice}</span>
                </div>
              ) : null}

              {error ? (
                <div className="boundary-error inventory-inline-error" role="alert">
                  <AlertTriangle size={15} />
                  <span>{error.message}</span>
                  {error.retryable ? (
                    <button className="btn" type="button" onClick={onRetryPreflight} disabled={isBusy}>
                      <RefreshCw size={14} /> Retry preflight
                    </button>
                  ) : null}
                </div>
              ) : null}

              <RequiredSection
                proposals={preflight.required_boundary_proposals}
                decisions={decisions}
                onDecisionChange={onDecisionChange}
              />

              <ExcludedSection
                preflight={preflight}
                decisions={decisions}
                isBusy={isBusy}
                onDecisionChange={onDecisionChange}
                onLoadMore={onLoadMore}
              />

              <RequestedPathSection
                preflight={preflight}
                pathInput={pathInput}
                requestedPaths={requestedPaths}
                decisions={decisions}
                isBusy={isBusy}
                onPathInputChange={setPathInput}
                onPathSubmit={handlePathSubmit}
                onRemoveRequestedPath={onRemoveRequestedPath}
                onDecisionChange={onDecisionChange}
              />

              <BlockedSection
                preflight={preflight}
                isBusy={isBusy}
                onExpand={onCheckPath}
              />

              {preflight.warnings.length > 0 ? (
                <section className="inventory-section" aria-labelledby="inventory-warnings-title">
                  <div className="inventory-section-heading">
                    <div>
                      <span className="eyebrow">Backend notices</span>
                      <h3 id="inventory-warnings-title">Inventory warnings</h3>
                    </div>
                  </div>
                  <ul className="inventory-warning-list">
                    {preflight.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                  </ul>
                </section>
              ) : null}
            </div>

            <div className="inventory-confirmation" aria-live="polite">
              <div>
                <strong>Confirmation summary</strong>
                {serialized.ok ? (
                  <span>{explicitDecisionCount} one-run decision{explicitDecisionCount === 1 ? "" : "s"} will be sent.</span>
                ) : (
                  <span className="is-pending">{serialized.reason}</span>
                )}
              </div>
              <div className={missingRequiredCount > 0 || !serialized.ok ? "is-pending" : "is-ready"}>
                {missingRequiredCount > 0
                  ? `${missingRequiredCount} required decision${missingRequiredCount === 1 ? "" : "s"} remaining`
                  : serialized.ok
                    ? "All required decisions are confirmed"
                    : "Conflicting decisions block this scan"}
              </div>
            </div>

            <footer className="boundary-actions inventory-actions">
              <button className="btn" type="button" onClick={onCancel} disabled={status === "submitting"}>
                Cancel
              </button>
              <button
                className="btn primary"
                type="button"
                onClick={onSubmit}
                disabled={missingRequiredCount > 0 || isBusy || !serialized.ok}
              >
                {status === "submitting" ? <LoaderCircle className="spin" size={14} /> : <Check size={14} />}
                {status === "submitting" ? "Starting scan..." : "Confirm and start scan"}
              </button>
            </footer>
          </>
        ) : null}
      </section>
    </div>
  );
}

function BlockingState({
  status,
  error,
  onRetry,
  onCancel,
}: {
  status: ProjectScanFlowStatus;
  error: ProjectScanFlowError | null;
  onRetry: () => void;
  onCancel: () => void;
}) {
  const stale = status === "stale";
  const baseline = status === "baseline_error";
  return (
    <div className={`inventory-blocking-state ${stale ? "is-stale" : "is-error"}`} role="alert">
      {stale ? <RefreshCw size={24} /> : <ShieldAlert size={24} />}
      <div>
        <span className="eyebrow">{stale ? "Preflight changed" : baseline ? "Baseline unavailable" : "Preflight error"}</span>
        <h3>
          {stale
            ? "Reload and review the inventory again"
            : baseline
              ? "The backend inventory policy did not pass its safety gate"
              : "Inventory preflight could not be created"}
        </h3>
        <p>
          {error?.message ??
            (stale
              ? "The project inventory changed before the scan started."
              : "The request could not be completed safely.")}
        </p>
        {stale ? (
          <p className="inventory-safety-copy">
            Previous decisions were cleared and will not be submitted automatically.
          </p>
        ) : baseline ? (
          <p className="inventory-safety-copy">
            No candidate controls are available, and the scan cannot bypass this backend gate.
          </p>
        ) : null}
      </div>
      <div className="inventory-blocking-actions">
        <button className="btn" type="button" onClick={onCancel}>Cancel</button>
        {(stale || error?.retryable) ? (
          <button className="btn primary" type="button" onClick={onRetry}>
            <RefreshCw size={14} /> {stale ? "Reload preflight" : "Retry preflight"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function InventoryIdentity({ preflight }: { preflight: ScanInventoryPreflightResponse }) {
  return (
    <div className="inventory-identity" aria-label="Backend inventory identity">
      <span><b>Baseline ready</b> · {preflight.source_mode.replace(/_/g, " ")}</span>
      <span>Policy <code>{preflight.inventory_policy_schema_version}</code></span>
      <span>Safety <code>{preflight.filesystem_safety_version}</code></span>
    </div>
  );
}

function InventorySummary({ preflight }: { preflight: ScanInventoryPreflightResponse }) {
  const values = [
    ["Included", preflight.summary.default_included_file_count],
    ["Needs review", preflight.summary.required_review_count],
    ["Excluded", preflight.summary.reviewable_excluded_count],
    ["Blocked", preflight.summary.hard_blocked_count],
    ["Missing", preflight.summary.missing_count],
    ["Collapsed", preflight.summary.collapsed_directory_count],
  ] as const;
  return (
    <dl className="inventory-summary" aria-label="Inventory summary">
      {values.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value.toLocaleString()}</dd>
        </div>
      ))}
    </dl>
  );
}

function RequiredSection({
  proposals,
  decisions,
  onDecisionChange,
}: {
  proposals: InventoryBoundaryProposal[];
  decisions: Record<string, ScanBoundaryAction>;
  onDecisionChange: Props["onDecisionChange"];
}) {
  return (
    <section className="inventory-section" aria-labelledby="inventory-required-title">
      <div className="inventory-section-heading">
        <div>
          <span className="eyebrow">Required confirmation</span>
          <h3 id="inventory-required-title">Needs your decision</h3>
        </div>
        <span className="inventory-count">{proposals.length}</span>
      </div>
      {proposals.length > 0 ? (
        <div className="boundary-list">
          {proposals.map((proposal) => (
            <InventoryProposal
              key={proposal.proposal_id}
              proposal={proposal}
              value={decisions[proposalIdentity(proposal)]}
              onChange={(decision) => onDecisionChange(proposal, decision)}
            />
          ))}
        </div>
      ) : (
        <EmptySection copy="No backend candidate requires a mandatory one-run decision." />
      )}
    </section>
  );
}

function ExcludedSection({
  preflight,
  decisions,
  isBusy,
  onDecisionChange,
  onLoadMore,
}: {
  preflight: ScanInventoryPreflightResponse;
  decisions: Record<string, ScanBoundaryAction>;
  isBusy: boolean;
  onDecisionChange: Props["onDecisionChange"];
  onLoadMore: () => void;
}) {
  const proposals = preflight.reviewable_excluded_page.items.filter(
    (proposal) => !preflight.required_boundary_proposals.some(
      (required) => required.proposal_id === proposal.proposal_id,
    ),
  );
  return (
    <section className="inventory-section" aria-labelledby="inventory-excluded-title">
      <div className="inventory-section-heading">
        <div>
          <span className="eyebrow">Prepared baseline</span>
          <h3 id="inventory-excluded-title">Excluded by default</h3>
        </div>
        <span className="inventory-count">{preflight.reviewable_excluded_page.total.toLocaleString()}</span>
      </div>
      <p className="inventory-section-copy">
        These backend-declared candidates stay skipped unless you explicitly include them for this run.
      </p>
      {proposals.length > 0 ? (
        <div className="boundary-list">
          {proposals.map((proposal) => (
            <InventoryProposal
              key={proposal.proposal_id}
              proposal={proposal}
              value={decisions[proposalIdentity(proposal)]}
              onChange={(decision) => onDecisionChange(proposal, decision)}
            />
          ))}
        </div>
      ) : (
        <EmptySection copy="No reviewable excluded candidate was returned on this page." />
      )}
      {preflight.reviewable_excluded_page.next_cursor ? (
        <button className="btn inventory-load-more" type="button" onClick={onLoadMore} disabled={isBusy}>
          <ChevronDown size={14} /> Load more excluded candidates
        </button>
      ) : null}
    </section>
  );
}

function RequestedPathSection({
  preflight,
  pathInput,
  requestedPaths,
  decisions,
  isBusy,
  onPathInputChange,
  onPathSubmit,
  onRemoveRequestedPath,
  onDecisionChange,
}: {
  preflight: ScanInventoryPreflightResponse;
  pathInput: string;
  requestedPaths: string[];
  decisions: Record<string, ScanBoundaryAction>;
  isBusy: boolean;
  onPathInputChange: (value: string) => void;
  onPathSubmit: (event: FormEvent) => void;
  onRemoveRequestedPath: (path: string) => void;
  onDecisionChange: Props["onDecisionChange"];
}) {
  const alreadyShown = new Set([
    ...preflight.required_boundary_proposals.map((proposal) => proposal.proposal_id),
    ...preflight.reviewable_excluded_page.items.map((proposal) => proposal.proposal_id),
  ]);
  const reviewable = preflight.requested_target_results.filter(
    (result) => result.status === "reviewable" && result.proposal && !alreadyShown.has(result.proposal.proposal_id),
  );

  return (
    <section className="inventory-section" aria-labelledby="inventory-path-title">
      <div className="inventory-section-heading">
        <div>
          <span className="eyebrow">Backend path check</span>
          <h3 id="inventory-path-title">Add exact file or folder path</h3>
        </div>
      </div>
      <p className="inventory-section-copy">
        Enter a project-relative POSIX path. The backend determines its type, policy outcome, safety, and bounded scope.
      </p>
      <form className="inventory-path-form" onSubmit={onPathSubmit}>
        <label>
          <span className="sr-only">Exact project-relative path</span>
          <FolderSearch size={15} />
          <input
            value={pathInput}
            onChange={(event) => onPathInputChange(event.target.value)}
            placeholder="src/experimental.py or packages/local-tool"
            autoComplete="off"
            disabled={isBusy}
          />
        </label>
        <button className="btn" type="submit" disabled={isBusy || !pathInput.trim()}>
          <FileSearch size={14} /> Check path
        </button>
      </form>
      {requestedPaths.length > 0 ? (
        <ul className="inventory-requested-paths" aria-label="Paths sent with this preflight">
          {requestedPaths.map((path) => (
            <li key={path}>
              <code>{path}</code>
              <button
                className="icon-btn"
                type="button"
                aria-label={`Remove ${path} from this preflight`}
                disabled={isBusy}
                onClick={() => onRemoveRequestedPath(path)}
              >
                <X size={13} />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {reviewable.length > 0 ? (
        <div className="boundary-list">
          {reviewable.map((result) => {
            const proposal = result.proposal!;
            return (
              <InventoryProposal
                key={proposal.proposal_id}
                proposal={proposal}
                value={decisions[proposalIdentity(proposal)]}
                onChange={(decision) => onDecisionChange(proposal, decision)}
              />
            );
          })}
        </div>
      ) : (
        <EmptySection copy="No additional reviewable exact path has been added." />
      )}
    </section>
  );
}

function BlockedSection({
  preflight,
  isBusy,
  onExpand,
}: {
  preflight: ScanInventoryPreflightResponse;
  isBusy: boolean;
  onExpand: (path: string) => void;
}) {
  const nonReviewable = preflight.requested_target_results.filter(
    (result): result is BlockedTargetView => result.status !== "reviewable",
  );
  // A requested path that is hard blocked is also a hard-blocked candidate in
  // the whole-repo enumeration, so it arrives on both lists.
  const resultPaths = new Set(nonReviewable.map((result) => result.target_path));
  const summaries = preflight.blocked_summaries.filter((summary) => !resultPaths.has(summary.path));
  const count = nonReviewable.length + summaries.length;
  return (
    <section className="inventory-section" aria-labelledby="inventory-blocked-title">
      <div className="inventory-section-heading">
        <div>
          <span className="eyebrow">Backend safety result</span>
          <h3 id="inventory-blocked-title">Cannot be scanned or needs expansion</h3>
        </div>
        <span className="inventory-count">{count}</span>
      </div>
      {count > 0 ? (
        <div className="inventory-result-list">
          {nonReviewable.map((result) => <BlockedResult key={`${result.target_path}:${result.status}`} result={result} />)}
          {summaries.map((summary) => (
            <article className="inventory-result" key={`${summary.path}:${summary.reason_code}`}>
              <ShieldAlert size={16} />
              <div>
                <code>{summary.path}</code>
                <p>
                  {summary.outcome === "collapsed_directory"
                    ? "Excluded by default; not expanded for this preflight."
                    : "Blocked by backend safety rules. This cannot be overridden."}
                </p>
                {summary.outcome === "collapsed_directory" ? (
                  <span>Excluded by default. Expand only if you need this folder this run.</span>
                ) : null}
                <span className="inventory-reason-code">Backend reason: {summary.reason_code}</span>
              </div>
              {summary.can_expand ? (
                <button className="btn" type="button" onClick={() => onExpand(summary.path)} disabled={isBusy}>
                  Expand with backend
                </button>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <EmptySection copy="The backend returned no blocked, missing, empty, or collapsed target summary." />
      )}
    </section>
  );
}

type BlockedTargetView = InventoryRequestedTargetView & {
  status: Exclude<InventoryRequestedTargetView["status"], "reviewable">;
};

// Keyed on the closed status enum from the contract rather than on backend
// reason codes, so the copy cannot drift out of sync with new codes.
const BLOCKED_RESULT_COPY: Record<BlockedTargetView["status"], string> = {
  hard_blocked: "Blocked by backend safety rules. This cannot be overridden.",
  missing: "Not found in the project.",
  empty_directory: "This folder has no files to review.",
  directory_limit_exceeded: "Too large to select as one folder; choose a smaller folder.",
};

function BlockedResult({ result }: { result: BlockedTargetView }) {
  const limit = result.limit_context;
  return (
    <article className="inventory-result">
      <ShieldAlert size={16} />
      <div>
        <code>{result.target_path}</code>
        <p>{BLOCKED_RESULT_COPY[result.status]}</p>
        {result.status === "directory_limit_exceeded" && limit ? (
          <span>
            Backend observed at least {limit.observed_at_least.toLocaleString()} for the {limit.limit_kind} limit
            of {limit.limit.toLocaleString()}.
          </span>
        ) : null}
        {result.reason_code ? (
          <span className="inventory-reason-code">Backend reason: {result.reason_code}</span>
        ) : null}
      </div>
    </article>
  );
}

function InventoryProposal({
  proposal,
  value,
  onChange,
}: {
  proposal: InventoryBoundaryProposal;
  value?: ScanBoundaryAction;
  onChange: (decision: ScanBoundaryAction) => void;
}) {
  const context = proposal.selection_context;
  const resolved = value ?? context.default_decision;
  const isDirectory = context.target_kind === "directory";
  const summary = context.directory_summary;
  return (
    <article className="boundary-item inventory-candidate">
      <div className="boundary-item-main">
        {isDirectory ? <FolderSearch size={18} /> : <ShieldAlert size={18} />}
        <div>
          <div className="inventory-candidate-title">
            <h4>{proposal.target.path}</h4>
            <span className={`inventory-default is-${context.base_outcome}`}>
              Default: {context.default_decision === "scan_this_run" ? "scan" : context.default_decision === "skip_this_run" ? "skip" : "confirm"}
            </span>
          </div>
          <p>{proposal.target.reason}</p>
          <div className="boundary-meta">
            <span>{proposal.target.risk_type}</span>
            <span>{context.target_kind}</span>
            <span>{context.selection_scope}</span>
            {context.exclusion_sources.map((source) => <span key={source}>source: {source}</span>)}
            {context.matched_inventory_policy_ids.map((policy) => <span key={policy}>policy: {policy}</span>)}
          </div>
        </div>
      </div>

      {summary ? (
        <dl className="inventory-directory-summary">
          <div><dt>Selectable</dt><dd>{summary.selectable_file_count.toLocaleString()}</dd></div>
          <div><dt>Blocked</dt><dd>{summary.pre_content_hard_blocked_count.toLocaleString()}</dd></div>
          <div><dt>Sensitive</dt><dd>{summary.sensitive_file_count.toLocaleString()}</dd></div>
          <div><dt>Bytes</dt><dd>{formatBytes(summary.selectable_bytes)}</dd></div>
          <div><dt>Max depth</dt><dd>{summary.observed_max_relative_depth}</dd></div>
        </dl>
      ) : null}

      <div className="boundary-choice" role="group" aria-label={`One-run decision for ${proposal.target.path}`}>
        {proposal.available_actions.includes("scan_this_run") ? (
          <button
            className={resolved === "scan_this_run" ? "is-active" : ""}
            type="button"
            aria-pressed={resolved === "scan_this_run"}
            disabled={!context.override_allowed}
            onClick={() => onChange("scan_this_run")}
          >
            <Check size={14} />
            {isDirectory ? "Scan all selectable files" : "Scan this run"}
          </button>
        ) : null}
        {proposal.available_actions.includes("skip_this_run") ? (
          <button
            className={resolved === "skip_this_run" ? "is-active" : ""}
            type="button"
            aria-pressed={resolved === "skip_this_run"}
            disabled={!context.override_allowed}
            onClick={() => onChange("skip_this_run")}
          >
            <AlertTriangle size={14} />
            {isDirectory ? "Skip all selectable files" : "Skip this run"}
          </button>
        ) : null}
      </div>
    </article>
  );
}

function EmptySection({ copy }: { copy: string }) {
  return <div className="inventory-empty">{copy}</div>;
}

function formatBytes(bytes: number) {
  if (bytes < 1_000) return `${bytes} B`;
  if (bytes < 1_000_000) return `${(bytes / 1_000).toFixed(1)} KB`;
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}
