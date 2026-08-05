import { useCallback, useMemo, useRef, useState } from "react";
import { ZodError } from "zod";
import { ApiRequestError } from "../services/http";
import {
  createScanPreflight,
  importProject,
  startProjectScan,
} from "../services/projectScanApi";
import type {
  InventoryBoundaryProposal,
  InventorySelectionSummary,
  ProjectImportResponse,
  ScanBoundaryAction,
  ScanBoundaryDecision,
  ScanCreateResponse,
  ScanInventoryPreflightResponse,
} from "../types";

export type ProjectScanFlowStatus =
  | "idle"
  | "importing"
  | "preflighting"
  | "reviewing"
  | "submitting"
  | "stale"
  | "baseline_error"
  | "error"
  | "completed";

export type ProjectScanFlowError = {
  kind: "baseline" | "stale" | "api";
  message: string;
  code?: string;
  retryable: boolean;
};

/** Serializing one-run decisions can fail closed, so callers get a result. */
export type InventoryDecisionSerialization =
  | { ok: true; decisions: ScanBoundaryDecision[] }
  | { ok: false; reason: string };

type ProgressUpdate = {
  running: boolean;
  stage: string;
  message: string;
  percent: number;
  status: "running" | "waiting" | "completed" | "error";
};

type Options = {
  apiBaseUrl: string;
  onCompleted: (
    projectId: string,
    response: ScanCreateResponse,
    // The viewer refresh awaits the network, so it must be able to check that
    // this scan run still owns the session before it mutates shared state.
    isCurrent: () => boolean,
  ) => Promise<void>;
  onProgress: (progress: ProgressUpdate) => void;
};

type PreflightOutcome = "accepted" | "failed" | "superseded";

const BASELINE_ERROR_CODES = new Set(["inventory_rules_unavailable", "inventory_rules_invalid"]);
const STALE_ERROR_CODES = new Set([
  "inventory_preflight_stale",
  "inventory_selection_target_changed",
  "inventory_selection_target_missing",
]);

// Raw parser output must never reach the dialog (step-02 §7 forbids rendering
// raw exceptions), so schema drift gets one fixed, safe sentence instead.
const CONTRACT_MISMATCH_MESSAGE =
  "The backend response did not match the expected inventory contract. Reload the preflight, or check that the API server matches this build.";

export function proposalIdentity(proposal: InventoryBoundaryProposal) {
  return [
    proposal.target.path,
    proposal.selection_context.selection_scope,
    proposal.target.fingerprint,
  ].join("\u001f");
}

export function collectInventoryProposals(preflight: ScanInventoryPreflightResponse) {
  const proposals = [
    ...preflight.required_boundary_proposals,
    ...preflight.reviewable_excluded_page.items,
    ...preflight.requested_target_results.flatMap((result) =>
      result.status === "reviewable" && result.proposal ? [result.proposal] : [],
    ),
  ];
  return [...new Map(proposals.map((proposal) => [proposal.proposal_id, proposal])).values()];
}

/**
 * Two preflight responses describe the same backend enumeration. Requested
 * paths and pagination do not affect these fields, so this is true across an
 * exact-path lookup or a `Load more`, and false once the repo or policy moved.
 */
export function sameInventoryBaseline(
  a: ScanInventoryPreflightResponse,
  b: ScanInventoryPreflightResponse,
) {
  return (
    a.preflight_request_id === b.preflight_request_id &&
    a.candidate_set_digest === b.candidate_set_digest &&
    a.inventory_policy_digest === b.inventory_policy_digest &&
    a.filesystem_safety_version === b.filesystem_safety_version
  );
}

export function decisionsForInventory(
  preflight: ScanInventoryPreflightResponse,
  decisionsByIdentity: Record<string, ScanBoundaryAction>,
): InventoryDecisionSerialization {
  const serialized = new Map<string, ScanBoundaryDecision>();

  for (const proposal of collectInventoryProposals(preflight)) {
    const context = proposal.selection_context;
    const choice = decisionsByIdentity[proposalIdentity(proposal)];
    if (!choice) continue;
    if (!context.decision_required && choice === context.default_decision) continue;

    const decision: ScanBoundaryDecision = {
      target_path: proposal.target.path,
      fingerprint: proposal.target.fingerprint,
      decision: choice,
      selection_scope: context.selection_scope,
    };
    const targetScopeKey = `${decision.target_path}\u001f${decision.selection_scope}`;
    const previous = serialized.get(targetScopeKey);
    if (
      previous &&
      (previous.fingerprint !== decision.fingerprint || previous.decision !== decision.decision)
    ) {
      return {
        ok: false,
        reason: `"${decision.target_path}" has conflicting one-run decisions. Reload the preflight before starting the scan.`,
      };
    }
    serialized.set(targetScopeKey, decision);
  }

  return { ok: true, decisions: [...serialized.values()] };
}

function mergeProposalPages(
  current: ScanInventoryPreflightResponse | null,
  next: ScanInventoryPreflightResponse,
  appendExcluded: boolean,
) {
  // Pages loaded from an earlier enumeration stay valid only while the backend
  // baseline is unchanged; a new candidate set supersedes every earlier page,
  // including the fingerprints any kept choice is keyed to.
  if (!current || !sameInventoryBaseline(current, next)) return next;
  const combined = [
    ...current.reviewable_excluded_page.items,
    ...next.reviewable_excluded_page.items,
  ];
  return {
    ...next,
    reviewable_excluded_page: {
      ...next.reviewable_excluded_page,
      items: [...new Map(combined.map((proposal) => [proposal.proposal_id, proposal])).values()],
      // A page-1 refresh (exact path lookup, folder expansion) must not rewind
      // pagination that already advanced, or `Load more` would restart at page 2.
      next_cursor: appendExcluded
        ? next.reviewable_excluded_page.next_cursor
        : current.reviewable_excluded_page.next_cursor,
    },
  };
}

function flowError(error: unknown, kind: ProjectScanFlowError["kind"] = "api"): ProjectScanFlowError {
  if (error instanceof ApiRequestError) {
    return {
      kind,
      message: error.message,
      code: error.code,
      retryable: error.retryable ?? true,
    };
  }
  if (error instanceof ZodError) {
    return { kind, message: CONTRACT_MISMATCH_MESSAGE, retryable: true };
  }
  return {
    kind,
    message: error instanceof Error ? error.message : "The request could not be completed.",
    retryable: true,
  };
}

export function useProjectScanFlow({ apiBaseUrl, onCompleted, onProgress }: Options) {
  const [status, setStatus] = useState<ProjectScanFlowStatus>("idle");
  const [session, setSession] = useState<ProjectImportResponse | null>(null);
  const [preflight, setPreflightState] = useState<ScanInventoryPreflightResponse | null>(null);
  const [decisionsByIdentity, setDecisionsState] = useState<Record<string, ScanBoundaryAction>>({});
  const [requestedPaths, setRequestedPathsState] = useState<string[]>([]);
  const [error, setError] = useState<ProjectScanFlowError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastSelectionSummary, setLastSelectionSummary] = useState<InventorySelectionSummary | null>(null);
  const preflightRef = useRef<ScanInventoryPreflightResponse | null>(null);
  const decisionsRef = useRef<Record<string, ScanBoundaryAction>>({});
  const requestedPathsRef = useRef<string[]>([]);
  const operationEpoch = useRef(0);
  // POST /api/scans is not idempotent — each accepted call materializes a
  // snapshot and a build — so the double-submit guard lives here, not only on
  // the disabled state of the confirm button.
  const submitInFlight = useRef(false);

  const setPreflight = useCallback((value: ScanInventoryPreflightResponse | null) => {
    preflightRef.current = value;
    setPreflightState(value);
  }, []);

  const setDecisions = useCallback((value: Record<string, ScanBoundaryAction>) => {
    decisionsRef.current = value;
    setDecisionsState(value);
  }, []);

  const setRequestedPaths = useCallback((value: string[]) => {
    requestedPathsRef.current = value;
    setRequestedPathsState(value);
  }, []);

  const clearOneRunState = useCallback(() => {
    setPreflight(null);
    setDecisions({});
    setRequestedPaths([]);
    setNotice(null);
  }, [setDecisions, setPreflight, setRequestedPaths]);

  const acceptPreflight = useCallback(
    (
      next: ScanInventoryPreflightResponse,
      options: { appendExcluded: boolean; preserveDecisions: boolean },
    ) => {
      const current = preflightRef.current;
      const supersededBaseline = current != null && !sameInventoryBaseline(current, next);
      const merged = mergeProposalPages(current, next, options.appendExcluded);
      setPreflight(merged);

      let droppedDecisions = 0;
      if (options.preserveDecisions) {
        const validIdentities = new Set(collectInventoryProposals(merged).map(proposalIdentity));
        const previous = decisionsRef.current;
        const kept = Object.fromEntries(
          Object.entries(previous).filter(([identity]) => validIdentities.has(identity)),
        );
        droppedDecisions = Object.keys(previous).length - Object.keys(kept).length;
        setDecisions(kept);
      } else {
        setDecisions({});
      }

      setError(null);
      // Losing a choice is never silent: the user has to know what is no longer
      // part of the submission before they press confirm.
      setNotice(
        droppedDecisions > 0
          ? `${droppedDecisions} earlier ${droppedDecisions === 1 ? "choice was" : "choices were"} dropped because the backend inventory changed. Review the scope again before starting the scan.`
          : supersededBaseline
            ? "The backend inventory changed, so this review was reloaded from a fresh preflight."
            : null,
      );
      setStatus("reviewing");
    },
    [setDecisions, setPreflight],
  );

  const requestPreflight = useCallback(
    async (
      currentSession: ProjectImportResponse,
      paths: string[],
      cursor: string | null,
      options: {
        appendExcluded: boolean;
        preserveDecisions: boolean;
        keepReviewOnError?: boolean;
        epoch: number;
      },
    ): Promise<PreflightOutcome> => {
      setStatus("preflighting");
      setError(null);
      onProgress({
        running: true,
        stage: "inventory",
        message: cursor ? "Loading more backend inventory candidates." : "Preparing scan inventory.",
        percent: 12,
        status: "running",
      });

      try {
        const next = await createScanPreflight(apiBaseUrl, {
          projectId: currentSession.project_id,
          requestedPaths: paths,
          reviewableExcludedCursor: cursor,
          reviewableExcludedLimit: 100,
        });
        if (options.epoch !== operationEpoch.current) return "superseded";
        if (next.project_id !== currentSession.project_id) {
          throw new Error("Preflight response does not match the imported project.");
        }
        acceptPreflight(next, options);
        onProgress({
          running: true,
          stage: "inventory",
          message: "Review the backend-prepared scan scope.",
          percent: 15,
          status: "waiting",
        });
        return "accepted";
      } catch (caught) {
        if (options.epoch !== operationEpoch.current) return "superseded";
        const normalized = flowError(caught);
        if (normalized.code && BASELINE_ERROR_CODES.has(normalized.code)) {
          clearOneRunState();
          setError({ ...normalized, kind: "baseline" });
          setStatus("baseline_error");
        } else if (options.keepReviewOnError && preflightRef.current) {
          setError(normalized);
          setStatus("reviewing");
        } else {
          setError(normalized);
          setStatus("error");
        }
        onProgress({
          running: false,
          stage: "inventory",
          message: normalized.message,
          percent: 15,
          status: "error",
        });
        return "failed";
      }
    },
    [acceptPreflight, apiBaseUrl, clearOneRunState, onProgress],
  );

  const start = useCallback(
    async (projectPath: string) => {
      const path = projectPath.trim();
      if (!path) return;
      const epoch = ++operationEpoch.current;
      clearOneRunState();
      setSession(null);
      setLastSelectionSummary(null);
      setError(null);
      setStatus("importing");
      onProgress({
        running: true,
        stage: "project",
        message: "Importing project.",
        percent: 5,
        status: "running",
      });

      try {
        const imported = await importProject(apiBaseUrl, path);
        if (epoch !== operationEpoch.current) return;
        setSession(imported);
        await requestPreflight(imported, [], null, {
          appendExcluded: false,
          preserveDecisions: false,
          epoch,
        });
      } catch (caught) {
        if (epoch !== operationEpoch.current) return;
        const normalized = flowError(caught);
        setError(normalized);
        setStatus("error");
        onProgress({
          running: false,
          stage: "project",
          message: normalized.message,
          percent: 5,
          status: "error",
        });
      }
    },
    [apiBaseUrl, clearOneRunState, onProgress, requestPreflight],
  );

  const retryPreflight = useCallback(async () => {
    if (!session) return;
    const epoch = ++operationEpoch.current;
    // A stale or failed baseline must not be restorable. Dropping it before the
    // reload keeps a failed retry on the blocking screen instead of falling
    // back to review controls bound to a superseded preflight_request_id.
    setPreflight(null);
    setDecisions({});
    await requestPreflight(session, requestedPathsRef.current, null, {
      appendExcluded: false,
      preserveDecisions: false,
      epoch,
    });
  }, [requestPreflight, session, setDecisions, setPreflight]);

  const checkPath = useCallback(
    async (path: string) => {
      if (!session || status !== "reviewing") return;
      const normalizedPath = path.trim();
      if (!normalizedPath) {
        setError({
          kind: "api",
          message: "Enter an exact project-relative file or folder path.",
          retryable: false,
        });
        return;
      }
      const previousPaths = requestedPathsRef.current;
      const paths = [...new Set([...previousPaths, normalizedPath])];
      setRequestedPaths(paths);
      const epoch = ++operationEpoch.current;
      const outcome = await requestPreflight(session, paths, null, {
        appendExcluded: false,
        preserveDecisions: true,
        keepReviewOnError: true,
        epoch,
      });
      // The backend normalizes every requested path up front, so one rejected
      // entry fails the whole preflight. Keeping it would make every later
      // lookup, page load and retry fail identically with no way back.
      if (outcome === "failed") setRequestedPaths(previousPaths);
    },
    [requestPreflight, session, setRequestedPaths, status],
  );

  const removeRequestedPath = useCallback(
    async (path: string) => {
      if (!session || status !== "reviewing") return;
      const previousPaths = requestedPathsRef.current;
      if (!previousPaths.includes(path)) return;
      const paths = previousPaths.filter((item) => item !== path);
      setRequestedPaths(paths);
      const epoch = ++operationEpoch.current;
      const outcome = await requestPreflight(session, paths, null, {
        appendExcluded: false,
        preserveDecisions: true,
        keepReviewOnError: true,
        epoch,
      });
      if (outcome === "failed") setRequestedPaths(previousPaths);
    },
    [requestPreflight, session, setRequestedPaths, status],
  );

  const loadMore = useCallback(async () => {
    const cursor = preflightRef.current?.reviewable_excluded_page.next_cursor;
    if (!session || !cursor || status !== "reviewing") return;
    const epoch = ++operationEpoch.current;
    await requestPreflight(session, requestedPathsRef.current, cursor, {
      appendExcluded: true,
      preserveDecisions: true,
      keepReviewOnError: true,
      epoch,
    });
  }, [requestPreflight, session, status]);

  const setDecision = useCallback(
    (proposal: InventoryBoundaryProposal, decision: ScanBoundaryAction) => {
      const context = proposal.selection_context;
      if (!context.override_allowed || !proposal.available_actions.includes(decision)) return;
      const identity = proposalIdentity(proposal);
      const next = { ...decisionsRef.current };
      if (!context.decision_required && decision === context.default_decision) {
        delete next[identity];
      } else {
        next[identity] = decision;
      }
      setDecisions(next);
      setError(null);
      setNotice(null);
    },
    [setDecisions],
  );

  const missingRequiredCount = useMemo(() => {
    if (!preflight) return 0;
    return collectInventoryProposals(preflight).filter(
      (proposal) =>
        proposal.selection_context.decision_required &&
        !decisionsByIdentity[proposalIdentity(proposal)],
    ).length;
  }, [decisionsByIdentity, preflight]);

  const serializedDecisions = useMemo<InventoryDecisionSerialization>(
    () =>
      preflight
        ? decisionsForInventory(preflight, decisionsByIdentity)
        : { ok: true, decisions: [] },
    [decisionsByIdentity, preflight],
  );

  const submit = useCallback(async () => {
    if (!session || !preflight || missingRequiredCount > 0) return;
    if (submitInFlight.current) return;
    if (!serializedDecisions.ok) {
      setError({ kind: "api", message: serializedDecisions.reason, retryable: true });
      return;
    }
    submitInFlight.current = true;
    const epoch = ++operationEpoch.current;
    setStatus("submitting");
    setError(null);
    setNotice(null);
    onProgress({
      running: true,
      stage: "scan",
      message: "Scanning the confirmed one-run inventory.",
      percent: 30,
      status: "running",
    });

    try {
      const response = await startProjectScan(apiBaseUrl, {
        projectId: session.project_id,
        preflightRequestId: preflight.preflight_request_id,
        boundaryDecisions: serializedDecisions.decisions,
      });
      if (epoch !== operationEpoch.current) return;
      if (response.project_id !== session.project_id) {
        throw new Error("Scan response does not match the imported project.");
      }

      if (response.status === "requires_boundary_decision") {
        const current = preflightRef.current;
        if (!current) throw new Error("The pending scan response has no active preflight.");
        const mergedRequired = [
          ...current.required_boundary_proposals,
          ...response.boundary_proposals,
        ];
        const next = {
          ...current,
          preflight_request_id: response.preflight_request_id ?? current.preflight_request_id,
          required_boundary_proposals: [
            ...new Map(mergedRequired.map((proposal) => [proposal.proposal_id, proposal])).values(),
          ],
        };
        acceptPreflight(next, { appendExcluded: false, preserveDecisions: true });
        setNotice("The scan is pending additional backend-required decisions. Review the highlighted scope and continue.");
        onProgress({
          running: true,
          stage: "inventory",
          message: "Scan pending additional inventory decisions.",
          percent: 15,
          status: "waiting",
        });
        return;
      }

      if (response.status === "error") {
        const normalized: ProjectScanFlowError = {
          kind: "api",
          message: "The backend reported a scan error before publishing a build.",
          retryable: true,
        };
        setError(normalized);
        setStatus("reviewing");
        onProgress({
          running: false,
          stage: "scan",
          message: normalized.message,
          percent: 30,
          status: "error",
        });
        return;
      }

      setLastSelectionSummary(response.inventory_selection_summary ?? null);
      clearOneRunState();
      setSession(null);
      setStatus("completed");
      await onCompleted(
        response.project_id,
        response,
        () => epoch === operationEpoch.current,
      );
      if (epoch !== operationEpoch.current) return;
      onProgress({
        running: false,
        stage: "map",
        message: "Scan completed. Latest project build loaded.",
        percent: 100,
        status: "completed",
      });
    } catch (caught) {
      if (epoch !== operationEpoch.current) return;
      const normalized = flowError(caught);
      if (normalized.code && STALE_ERROR_CODES.has(normalized.code)) {
        setDecisions({});
        setError({ ...normalized, kind: "stale" });
        setStatus("stale");
        onProgress({
          running: false,
          stage: "inventory",
          message: "The inventory changed. Reload and confirm a new preflight.",
          percent: 15,
          status: "waiting",
        });
      } else if (normalized.code && BASELINE_ERROR_CODES.has(normalized.code)) {
        clearOneRunState();
        setError({ ...normalized, kind: "baseline" });
        setStatus("baseline_error");
        onProgress({
          running: false,
          stage: "inventory",
          message: normalized.message,
          percent: 15,
          status: "error",
        });
      } else {
        setError(normalized);
        setStatus(preflightRef.current ? "reviewing" : "error");
        onProgress({
          running: false,
          stage: "scan",
          message: normalized.message,
          percent: 30,
          status: "error",
        });
      }
    } finally {
      submitInFlight.current = false;
    }
  }, [
    acceptPreflight,
    apiBaseUrl,
    clearOneRunState,
    missingRequiredCount,
    onCompleted,
    onProgress,
    preflight,
    serializedDecisions,
    session,
    setDecisions,
  ]);

  const cancel = useCallback(() => {
    operationEpoch.current += 1;
    clearOneRunState();
    setSession(null);
    setError(null);
    setStatus("idle");
    onProgress({
      running: false,
      stage: "idle",
      message: "Scan cancelled before a build was created.",
      percent: 0,
      status: "waiting",
    });
  }, [clearOneRunState, onProgress]);

  const dialogOpen =
    session != null &&
    ["preflighting", "reviewing", "submitting", "stale", "baseline_error", "error"].includes(status);
  const isBusy = status === "importing" || status === "preflighting" || status === "submitting";

  return {
    status,
    session,
    preflight,
    decisionsByIdentity,
    requestedPaths,
    error,
    notice,
    lastSelectionSummary,
    missingRequiredCount,
    dialogOpen,
    isBusy,
    externalError: dialogOpen ? undefined : error?.message,
    start,
    retryPreflight,
    checkPath,
    removeRequestedPath,
    loadMore,
    setDecision,
    submit,
    cancel,
  };
}
