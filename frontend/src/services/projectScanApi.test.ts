import { afterEach, describe, expect, it, vi } from "vitest";
import preflightRequestSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-preflight-request-sample.json";
import preflightResponseSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-preflight-response-sample.json";
import staleErrorSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-preflight-stale-error-sample.json";
import rulesInvalidSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-rules-invalid-error-sample.json";
import rulesUnavailableSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-rules-unavailable-error-sample.json";
import scanCompletedSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-scan-completed-response-sample.json";
import scanPendingSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-scan-pending-response-sample.json";
import scanSelectionRequestSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-scan-selection-request-sample.json";
import { scanBoundaryDecisionSchema } from "../types";
import { ApiRequestError } from "./http";
import { createScanPreflight, startProjectScan } from "./projectScanApi";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "Unprocessable Entity",
    headers: { "Content-Type": "application/json" },
  });
}

describe("projectScanApi Inventory Preflight contract", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("serializes the formal preflight request and parses the backend sample", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(preflightResponseSample));
    vi.stubGlobal("fetch", fetchMock);

    const response = await createScanPreflight("http://127.0.0.1:8000/", {
      projectId: "project:sample-ai-health-rag",
      requestedPaths: preflightRequestSample.requested_paths,
      reviewableExcludedCursor: preflightRequestSample.reviewable_excluded_cursor,
      reviewableExcludedLimit: preflightRequestSample.reviewable_excluded_limit,
    });

    expect(response.preflight_request_id).toBe("preflight:9d13-sample");
    expect(response.requested_target_results[1].proposal?.selection_context.directory_summary).toMatchObject({
      selectable_file_count: 23,
      pre_content_hard_blocked_count: 3,
    });
    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "http://127.0.0.1:8000/api/projects/project%3Asample-ai-health-rag/scan-preflights",
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual(preflightRequestSample);
  });

  it("forwards exact backend identity, fingerprint, and scope in the scan request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(scanCompletedSample));
    vi.stubGlobal("fetch", fetchMock);

    const response = await startProjectScan("http://127.0.0.1:8000", {
      projectId: scanSelectionRequestSample.project_id,
      preflightRequestId: scanSelectionRequestSample.preflight_request_id,
      boundaryDecisions: scanSelectionRequestSample.boundary_decisions.map((decision) =>
        scanBoundaryDecisionSchema.parse(decision),
      ),
    });

    expect(response.status).toBe("completed");
    if (response.status !== "completed") {
      throw new Error("Expected the completed scan response fixture.");
    }
    expect(response.scan_id).toBe("scan:sample-s1");
    expect(response.inventory_selection_summary?.directory_scope_results[0]).toMatchObject({
      target_path: "node_modules/small-local-package",
      observed_file_count: 26,
      included_file_count: 22,
      hard_blocked_file_count: 3,
      post_decision_blocked_file_count: 1,
    });
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual(scanSelectionRequestSample);
    expect(String(fetchMock.mock.calls[0][0])).not.toContain("/api/map");
  });

  it("parses a pending response without inventing a scan id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(scanPendingSample)));

    const response = await startProjectScan("http://api", {
      projectId: scanPendingSample.project_id,
      preflightRequestId: scanPendingSample.preflight_request_id,
      boundaryDecisions: [],
    });

    expect(response.status).toBe("requires_boundary_decision");
    expect("scan_id" in response).toBe(false);
    if (response.status !== "requires_boundary_decision") {
      throw new Error("Expected the pending scan response fixture.");
    }
    // Narrowing, not just the runtime shape: the pending branch of the union
    // must make `scan_id` unreachable so no caller can treat it as completed.
    // @ts-expect-error `scan_id` is absent from the pending response contract.
    void response.scan_id;
    expect(response.boundary_proposals[0].selection_context.selection_scope).toBe("exact_file");
  });

  it.each([
    ["inventory_rules_unavailable", rulesUnavailableSample],
    ["inventory_rules_invalid", rulesInvalidSample],
  ])("preserves typed fail-closed %s errors without raw context", async (code, sample) => {
    const body = {
      ...sample,
      detail: {
        ...sample.detail,
        context: { raw_secret: "DO-NOT-RENDER", absolute_path: "C:\\private\\policy.toml" },
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, 422)));

    const request = createScanPreflight("http://api", { projectId: "project:p1" });
    await expect(request).rejects.toMatchObject({
      name: ApiRequestError.name,
      code,
      message: sample.detail.message,
      retryable: false,
    });
    await expect(request).rejects.not.toThrow(/DO-NOT-RENDER|private\\policy/);
  });

  it("normalizes stale errors for explicit user-driven reload", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(staleErrorSample, 409)));

    await expect(
      startProjectScan("http://api", {
        projectId: "project:p1",
        preflightRequestId: "preflight:p1",
        boundaryDecisions: [],
      }),
    ).rejects.toMatchObject({
      code: "inventory_preflight_stale",
      retryable: true,
    });
  });

  it("rejects malformed enum values and unsafe absolute candidate paths", async () => {
    const malformed = structuredClone(preflightResponseSample);
    malformed.source_mode = "frontend_inferred";
    malformed.required_boundary_proposals[0].target.path = "C:\\private\\.env";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(malformed)));

    await expect(
      createScanPreflight("http://api", { projectId: "project:sample-ai-health-rag" }),
    ).rejects.toThrow();
  });
});
