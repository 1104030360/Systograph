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
    expect(onCompleted).toHaveBeenCalledWith(session.project_id, completedResponse);
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
});
