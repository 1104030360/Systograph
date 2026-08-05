import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import preflightResponseSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-preflight-response-sample.json";
import scanCompletedSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-scan-completed-response-sample.json";
import scanPendingSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-scan-pending-response-sample.json";
import { ApiRequestError } from "../services/http";
import {
  createScanPreflight,
  importProject,
  startProjectScan,
} from "../services/projectScanApi";
import {
  scanCreateResponseSchema,
  scanInventoryPreflightResponseSchema,
  type ScanInventoryPreflightResponse,
} from "../types";
import { proposalIdentity, useProjectScanFlow } from "./useProjectScanFlow";

vi.mock("../services/projectScanApi", () => ({
  createScanPreflight: vi.fn(),
  importProject: vi.fn(),
  startProjectScan: vi.fn(),
}));

const session = {
  project_id: "project:sample-ai-health-rag",
  source_type: "local_path" as const,
  project_name: "sample-ai-health-rag",
  project_path: "C:\\safe-fixture",
};

const samplePreflight = scanInventoryPreflightResponseSchema.parse(preflightResponseSample);
const completedResponse = scanCreateResponseSchema.parse(scanCompletedSample);
const pendingResponse = scanCreateResponseSchema.parse(scanPendingSample);

function emptyPreflight(): ScanInventoryPreflightResponse {
  return {
    ...samplePreflight,
    preflight_request_id: "preflight:empty",
    summary: {
      default_included_file_count: 0,
      required_review_count: 0,
      reviewable_excluded_count: 0,
      hard_blocked_count: 0,
      missing_count: 0,
      collapsed_directory_count: 0,
    },
    required_boundary_proposals: [],
    reviewable_excluded_page: { items: [], next_cursor: null, total: 0 },
    requested_target_results: [],
    blocked_summaries: [],
    warnings: [],
  };
}

function setupHook() {
  const onCompleted = vi.fn().mockResolvedValue(undefined);
  const onProgress = vi.fn();
  const hook = renderHook(() =>
    useProjectScanFlow({
      apiBaseUrl: "http://api",
      onCompleted,
      onProgress,
    }),
  );
  return { ...hook, onCompleted, onProgress };
}

describe("useProjectScanFlow", () => {
  beforeEach(() => {
    vi.mocked(importProject).mockResolvedValue(session);
    vi.mocked(createScanPreflight).mockResolvedValue(samplePreflight);
    vi.mocked(startProjectScan).mockResolvedValue(completedResponse);
  });

  it("runs import → preflight → explicit decisions → completed viewer refresh", async () => {
    const { result, onCompleted } = setupHook();

    await act(async () => result.current.start(session.project_path));
    expect(result.current.status).toBe("reviewing");
    expect(result.current.missingRequiredCount).toBe(2);

    const required = samplePreflight.required_boundary_proposals[0];
    const excluded = samplePreflight.reviewable_excluded_page.items[0];
    const directory = samplePreflight.requested_target_results[1].proposal!;
    act(() => {
      result.current.setDecision(required, "skip_this_run");
      result.current.setDecision(excluded, "scan_this_run");
      result.current.setDecision(directory, "scan_this_run");
    });
    expect(result.current.missingRequiredCount).toBe(0);

    await act(async () => result.current.submit());

    expect(startProjectScan).toHaveBeenCalledWith("http://api", {
      projectId: session.project_id,
      preflightRequestId: samplePreflight.preflight_request_id,
      boundaryDecisions: [
        {
          target_path: ".env",
          fingerprint: "sha256:metadata-env-sample",
          decision: "skip_this_run",
          selection_scope: "exact_file",
        },
        {
          target_path: "ignored/custom-loader.py",
          fingerprint: "sha256:metadata-ignored-loader-sample",
          decision: "scan_this_run",
          selection_scope: "exact_file",
        },
        {
          target_path: "node_modules/small-local-package",
          fingerprint: "sha256:directory-manifest-sample",
          decision: "scan_this_run",
          selection_scope: "recursive_directory",
        },
      ],
    });
    expect(onCompleted).toHaveBeenCalledWith(
      session.project_id,
      completedResponse,
      expect.any(Function),
    );
    expect(result.current.status).toBe("completed");
    expect(result.current.preflight).toBeNull();
    expect(result.current.requestedPaths).toEqual([]);
  });

  it("accepts a valid no-decision-needed baseline and sends an empty decision list", async () => {
    vi.mocked(createScanPreflight).mockResolvedValue(emptyPreflight());
    const { result } = setupHook();

    await act(async () => result.current.start(session.project_path));
    expect(result.current.missingRequiredCount).toBe(0);
    await act(async () => result.current.submit());

    expect(startProjectScan).toHaveBeenCalledWith(
      "http://api",
      expect.objectContaining({ boundaryDecisions: [] }),
    );
  });

  it("never resubmits stale decisions and requires an explicit preflight reload", async () => {
    vi.mocked(startProjectScan).mockRejectedValue(
      new ApiRequestError("Scan selection changed. Refresh the file review.", 409, {
        code: "inventory_preflight_stale",
        retryable: true,
        context: null,
      }),
    );
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));
    const required = samplePreflight.required_boundary_proposals[0];
    const directory = samplePreflight.requested_target_results[1].proposal!;
    act(() => {
      result.current.setDecision(required, "skip_this_run");
      result.current.setDecision(directory, "skip_this_run");
    });

    await act(async () => result.current.submit());
    expect(result.current.status).toBe("stale");
    expect(result.current.decisionsByIdentity).toEqual({});
    expect(createScanPreflight).toHaveBeenCalledTimes(1);
    expect(startProjectScan).toHaveBeenCalledTimes(1);

    vi.mocked(createScanPreflight).mockResolvedValue({
      ...samplePreflight,
      preflight_request_id: "preflight:fresh",
    });
    await act(async () => result.current.retryPreflight());
    expect(createScanPreflight).toHaveBeenCalledTimes(2);
    expect(startProjectScan).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe("reviewing");
    expect(result.current.decisionsByIdentity).toEqual({});
  });

  it.each(["inventory_rules_unavailable", "inventory_rules_invalid"])(
    "fails closed for %s and never calls the scan API",
    async (code) => {
      vi.mocked(createScanPreflight).mockRejectedValue(
        new ApiRequestError("The default inventory policy is not available.", 422, {
          code,
          retryable: false,
          context: { raw_secret: "DO-NOT-RENDER" },
        }),
      );
      const { result } = setupHook();

      await act(async () => result.current.start(session.project_path));
      expect(result.current.status).toBe("baseline_error");
      expect(result.current.preflight).toBeNull();
      expect(result.current.error).toMatchObject({ code, retryable: false });
      expect(result.current.error?.message).not.toContain("DO-NOT-RENDER");
      expect(startProjectScan).not.toHaveBeenCalled();
    },
  );

  it("recovers from a network/API preflight error only when the user retries", async () => {
    vi.mocked(createScanPreflight)
      .mockRejectedValueOnce(new ApiRequestError("Network request failed."))
      .mockResolvedValueOnce(emptyPreflight());
    const { result } = setupHook();

    await act(async () => result.current.start(session.project_path));
    expect(result.current.status).toBe("error");
    expect(result.current.dialogOpen).toBe(true);
    expect(createScanPreflight).toHaveBeenCalledTimes(1);

    await act(async () => result.current.retryPreflight());
    expect(result.current.status).toBe("reviewing");
    expect(createScanPreflight).toHaveBeenCalledTimes(2);
  });

  it("keeps a pending scan in review and completes only after the new required decision", async () => {
    vi.mocked(createScanPreflight).mockResolvedValue(emptyPreflight());
    vi.mocked(startProjectScan)
      .mockResolvedValueOnce(pendingResponse)
      .mockResolvedValueOnce(completedResponse);
    const { result, onCompleted } = setupHook();

    await act(async () => result.current.start(session.project_path));
    await act(async () => result.current.submit());
    expect(result.current.status).toBe("reviewing");
    expect(result.current.missingRequiredCount).toBe(1);
    expect(result.current.notice).toContain("pending");
    expect(onCompleted).not.toHaveBeenCalled();

    const pendingProposal = result.current.preflight!.required_boundary_proposals[0];
    act(() => result.current.setDecision(pendingProposal, "skip_this_run"));
    expect(result.current.decisionsByIdentity[proposalIdentity(pendingProposal)]).toBe("skip_this_run");
    await act(async () => result.current.submit());

    await waitFor(() => expect(onCompleted).toHaveBeenCalledOnce());
    expect(result.current.status).toBe("completed");
  });

  it("drops a path the backend rejects so later preflights are not poisoned", async () => {
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));

    vi.mocked(createScanPreflight).mockRejectedValueOnce(
      new ApiRequestError("Choose a project-relative path without glob syntax.", 422, {
        code: "inventory_selection_path_invalid",
        retryable: false,
        context: null,
      }),
    );
    await act(async () => result.current.checkPath("src/*.py"));

    expect(vi.mocked(createScanPreflight).mock.lastCall?.[1].requestedPaths).toEqual(["src/*.py"]);
    expect(result.current.requestedPaths).toEqual([]);
    expect(result.current.status).toBe("reviewing");

    // The next lookup must not resend the rejected entry, otherwise every
    // later preflight fails identically and only Cancel escapes the dialog.
    await act(async () => result.current.checkPath("src/experimental.py"));
    expect(vi.mocked(createScanPreflight).mock.lastCall?.[1].requestedPaths).toEqual([
      "src/experimental.py",
    ]);
    expect(result.current.requestedPaths).toEqual(["src/experimental.py"]);
  });

  it("removes a requested path on demand and re-preflights without it", async () => {
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));
    await act(async () => result.current.checkPath("src/experimental.py"));
    expect(result.current.requestedPaths).toEqual(["src/experimental.py"]);

    await act(async () => result.current.removeRequestedPath("src/experimental.py"));
    expect(result.current.requestedPaths).toEqual([]);
    expect(vi.mocked(createScanPreflight).mock.lastCall?.[1].requestedPaths).toEqual([]);
  });

  it("keeps earlier excluded pages and their choices across an exact-path lookup", async () => {
    const secondPage = {
      ...samplePreflight,
      reviewable_excluded_page: {
        items: [
          {
            ...samplePreflight.reviewable_excluded_page.items[0],
            proposal_id: "proposal:ignored-page-2",
            target: {
              ...samplePreflight.reviewable_excluded_page.items[0].target,
              path: "ignored/page-two.py",
              fingerprint: "sha256:metadata-page-two",
            },
          },
        ],
        next_cursor: null,
        total: 12,
      },
    };
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));

    vi.mocked(createScanPreflight).mockResolvedValueOnce(secondPage);
    await act(async () => result.current.loadMore());
    expect(vi.mocked(createScanPreflight).mock.lastCall?.[1].reviewableExcludedCursor).toBe(
      "cursor:reviewable-excluded-page-2-sample",
    );
    const pageTwoProposal = result.current.preflight!.reviewable_excluded_page.items.find(
      (item) => item.proposal_id === "proposal:ignored-page-2",
    )!;
    act(() => result.current.setDecision(pageTwoProposal, "scan_this_run"));

    // A page-1 refresh must not silently discard pages 2..N or the choices on
    // them; the baseline is unchanged, so both stay valid.
    await act(async () => result.current.checkPath("src/experimental.py"));

    const identities = result.current.preflight!.reviewable_excluded_page.items.map(
      (item) => item.proposal_id,
    );
    expect(identities).toContain("proposal:ignored-page-2");
    expect(result.current.decisionsByIdentity[proposalIdentity(pageTwoProposal)]).toBe(
      "scan_this_run",
    );
    expect(result.current.notice).toBeNull();
  });

  it("discards superseded pages and choices when the backend baseline changes", async () => {
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));
    const excluded = samplePreflight.reviewable_excluded_page.items[0];
    act(() => result.current.setDecision(excluded, "scan_this_run"));

    vi.mocked(createScanPreflight).mockResolvedValueOnce({
      ...samplePreflight,
      preflight_request_id: "preflight:rotated",
      candidate_set_digest: "sha256:candidates-rotated",
      reviewable_excluded_page: { items: [], next_cursor: null, total: 0 },
    });
    await act(async () => result.current.checkPath("src/experimental.py"));

    expect(result.current.preflight!.reviewable_excluded_page.items).toEqual([]);
    expect(result.current.decisionsByIdentity).toEqual({});
    expect(result.current.notice).toMatch(/dropped because the backend inventory changed/);
  });

  it("does not restore superseded review controls when a stale reload fails", async () => {
    vi.mocked(startProjectScan).mockRejectedValue(
      new ApiRequestError("Scan selection changed. Refresh the file review.", 409, {
        code: "inventory_preflight_stale",
        retryable: true,
        context: null,
      }),
    );
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));
    const required = samplePreflight.required_boundary_proposals[0];
    const directory = samplePreflight.requested_target_results[1].proposal!;
    act(() => {
      result.current.setDecision(required, "skip_this_run");
      result.current.setDecision(directory, "skip_this_run");
    });
    await act(async () => result.current.submit());
    expect(result.current.status).toBe("stale");

    vi.mocked(createScanPreflight).mockRejectedValueOnce(new ApiRequestError("Network request failed."));
    await act(async () => result.current.retryPreflight());

    // A failed reload must stay on the blocking screen. Keeping the old
    // preflight would let the user submit a known-superseded request id.
    expect(result.current.status).toBe("error");
    expect(result.current.preflight).toBeNull();
    expect(startProjectScan).toHaveBeenCalledTimes(1);
  });

  it("reports a schema mismatch without surfacing the raw parser exception", async () => {
    vi.mocked(createScanPreflight).mockRejectedValue(
      scanInventoryPreflightResponseSchema.safeParse({ source_mode: "frontend_inferred" })
        .error as unknown as Error,
    );
    const { result } = setupHook();

    await act(async () => result.current.start(session.project_path));

    expect(result.current.status).toBe("error");
    expect(result.current.error?.message).toBe(
      "The backend response did not match the expected inventory contract. Reload the preflight, or check that the API server matches this build.",
    );
    expect(result.current.error?.message).not.toMatch(/invalid_|"code"|received/);
  });

  it("never starts two scans from a double confirm", async () => {
    vi.mocked(createScanPreflight).mockResolvedValue(emptyPreflight());
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));

    await act(async () => {
      // POST /api/scans materializes a snapshot and a build, so a second
      // in-flight call would create a duplicate run.
      await Promise.all([result.current.submit(), result.current.submit()]);
    });

    expect(startProjectScan).toHaveBeenCalledTimes(1);
  });

  it("cancels without calling the scan API and clears one-run state", async () => {
    const { result } = setupHook();
    await act(async () => result.current.start(session.project_path));
    act(() =>
      result.current.setDecision(samplePreflight.required_boundary_proposals[0], "skip_this_run"),
    );

    act(() => result.current.cancel());

    expect(startProjectScan).not.toHaveBeenCalled();
    expect(result.current.status).toBe("idle");
    expect(result.current.preflight).toBeNull();
    expect(result.current.decisionsByIdentity).toEqual({});
    expect(result.current.requestedPaths).toEqual([]);
    expect(result.current.dialogOpen).toBe(false);
  });

  it("lets a superseded viewer refresh opt out through isCurrent", async () => {
    const { result, onCompleted } = setupHook();
    vi.mocked(createScanPreflight).mockResolvedValue(emptyPreflight());
    await act(async () => result.current.start(session.project_path));
    await act(async () => result.current.submit());

    const isCurrent = vi.mocked(onCompleted).mock.calls[0][2] as () => boolean;
    expect(isCurrent()).toBe(true);
    act(() => result.current.cancel());
    expect(isCurrent()).toBe(false);
  });
});
