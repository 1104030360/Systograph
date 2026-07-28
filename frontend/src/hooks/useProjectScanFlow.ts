import { useCallback, useMemo, useRef, useState } from "react";
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

type ProgressUpdate = {
  running: boolean;
  stage: string;
  message: string;
  percent: number;
  status: "running" | "waiting" | "completed" | "error";
};

type Options = {
  apiBaseUrl: string;
  onCompleted: (projectId: string, response: ScanCreateResponse) => Promise<void>;
  onProgress: (progress: ProgressUpdate) => void;
};

const BASELINE_ERROR_CODES = new Set(["inventory_rules_unavailable", "inventory_rules_invalid"]);
const STALE_ERROR_CODES = new Set([
  "inventory_preflight_stale",
  "inventory_selection_target_changed",
  "inventory_selection_target_missing",
]);

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

export function decisionsForInventory(
  preflight: ScanInventoryPreflightResponse,
  decisionsByIdentity: Record<string, ScanBoundaryAction>,
): ScanBoundaryDecision[] {
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
      throw new Error("Conflicting inventory decisions require a fresh preflight.");
    }
    serialized.set(targetScopeKey, decision);
  }

  return [...serialized.values()];
}

function mergeProposalPages(
  current: ScanInventoryPreflightResponse | null,
  next: ScanInventoryPreflightResponse,
  appendExcluded: boolean,
) {
  if (!appendExcluded || !current) return next;
  const combined = [
    ...current.reviewable_excluded_page.items,
    ...next.reviewable_excluded_page.items,
  ];
  return {
    ...next,
    reviewable_excluded_page: {
      ...next.reviewable_excluded_page,
      items: [...new Map(combined.map((proposal) => [proposal.proposal_id, proposal])).values()],
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
  const [decisionsByIdentity, setDecisionsByIdentity] = useState<Record<string, ScanBoundaryAction>>({});
  const [requestedPaths, setRequestedPaths] = useState<string[]>([]);
  const [error, setError] = useState<ProjectScanFlowError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastSelectionSummary, setLastSelectionSummary] = useState<InventorySelectionSummary | null>(null);
  const preflightRef = useRef<ScanInventoryPreflightResponse | null>(null);
  const operationEpoch = useRef(0);

  const setPreflight = useCallback((value: ScanInventoryPreflightResponse | null) => {
    preflightRef.current = value;
    setPreflightState(value);
  }, []);

  const clearOneRunState = useCallback(() => {
    setPreflight(null);
    setDecisionsByIdentity({});
    setRequestedPaths([]);
    setNotice(null);
  }, [setPreflight]);

  const acceptPreflight = useCallback(
    (
      next: ScanInventoryPreflightResponse,
      options: { appendExcluded: boolean; preserveDecisions: boolean },
    ) => {
      const merged = mergeProposalPages(preflightRef.current, next, options.appendExcluded);
      setPreflight(merged);
      setDecisionsByIdentity((current) => {
        if (!options.preserveDecisions) return {};
        const validIdentities = new Set(collectInventoryProposals(merged).map(proposalIdentity));
        return Object.fromEntries(
          Object.entries(current).filter(([identity]) => validIdentities.has(identity)),
        );
      });
      setError(null);
      setNotice(null);
      setStatus("reviewing");
    },
    [setPreflight],
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
    ) => {
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
        if (options.epoch !== operationEpoch.current) return;
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
      } catch (caught) {
        if (options.epoch !== operationEpoch.current) return;
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
    setDecisionsByIdentity({});
    await requestPreflight(session, requestedPaths, null, {
      appendExcluded: false,
      preserveDecisions: false,
      epoch,
    });
  }, [requestPreflight, requestedPaths, session]);

  const checkPath = useCallback(
    async (path: string) => {
      if (!session || status === "submitting" || status === "preflighting") return;
      const normalizedPath = path.trim();
      if (!normalizedPath) {
        setError({
          kind: "api",
          message: "Enter an exact project-relative file or folder path.",
          retryable: false,
        });
        return;
      }
      const paths = [...new Set([...requestedPaths, normalizedPath])];
      setRequestedPaths(paths);
      const epoch = ++operationEpoch.current;
      await requestPreflight(session, paths, null, {
        appendExcluded: false,
        preserveDecisions: true,
        keepReviewOnError: true,
        epoch,
      });
    },
    [requestPreflight, requestedPaths, session, status],
  );

  const loadMore = useCallback(async () => {
    const cursor = preflightRef.current?.reviewable_excluded_page.next_cursor;
    if (!session || !cursor || status === "submitting" || status === "preflighting") return;
    const epoch = ++operationEpoch.current;
    await requestPreflight(session, requestedPaths, cursor, {
      appendExcluded: true,
      preserveDecisions: true,
      keepReviewOnError: true,
      epoch,
    });
  }, [requestPreflight, requestedPaths, session, status]);

  const setDecision = useCallback(
    (proposal: InventoryBoundaryProposal, decision: ScanBoundaryAction) => {
      const context = proposal.selection_context;
      if (!context.override_allowed || !proposal.available_actions.includes(decision)) return;
      const identity = proposalIdentity(proposal);
      setDecisionsByIdentity((current) => {
        if (!context.decision_required && decision === context.default_decision) {
          const next = { ...current };
          delete next[identity];
          return next;
        }
        return { ...current, [identity]: decision };
      });
      setError(null);
      setNotice(null);
    },
    [],
  );

  const missingRequiredCount = useMemo(() => {
    if (!preflight) return 0;
    return collectInventoryProposals(preflight).filter(
      (proposal) =>
        proposal.selection_context.decision_required &&
        !decisionsByIdentity[proposalIdentity(proposal)],
    ).length;
  }, [decisionsByIdentity, preflight]);

  const submit = useCallback(async () => {
    if (!session || !preflight || missingRequiredCount > 0) return;
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
        boundaryDecisions: decisionsForInventory(preflight, decisionsByIdentity),
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
      await onCompleted(response.project_id, response);
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
        setDecisionsByIdentity({});
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
    }
  }, [
    acceptPreflight,
    apiBaseUrl,
    clearOneRunState,
    decisionsByIdentity,
    missingRequiredCount,
    onCompleted,
    onProgress,
    preflight,
    session,
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
    loadMore,
    setDecision,
    submit,
    cancel,
  };
}
