import type { PropsWithChildren } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import proposalSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-mapping-proposal-sample.json";
import { mapBuildScopedResponseSchema, parseMapBuildPayload } from "../contracts/viewer";
import { ApiRequestError } from "../services/http";
import { applyConfirmedMappings, loadLatestMapBuild } from "../services/mapBuildApi";
import { decideMappingProposal, listMappingProposals } from "../services/mappingApi";
import {
  mappingProposalDecisionResultSchema,
  mappingProposalSchema,
  type MappingProposalDecisionResult,
} from "../types";
import { useMappingProposal } from "./useMappingProposal";

vi.mock("../services/mappingApi", () => ({
  listMappingProposals: vi.fn(),
  createMappingProposal: vi.fn(),
  decideMappingProposal: vi.fn(),
}));

vi.mock("../services/mapBuildApi", () => ({
  applyConfirmedMappings: vi.fn(),
  loadLatestMapBuild: vi.fn(),
}));

const proposal = mappingProposalSchema.parse(proposalSample);

function buildResponse(baseBuildId: string, buildId: string) {
  const map = {
    schema_version: "ai-system-map/v2",
    system_type: "ai_system",
    scan_id: "scan:s1",
    build_id: buildId,
    environment_id: "environment:default-static",
    generated_from_build_id: buildId,
    project: { project_id: proposal.project_id, name: "demo", root_path: null, path_mode: "redacted" },
    components: [], edges: [], evidence: [], endpoints: [], risk_hints: [], unmapped_components: [],
  };
  const graph = {
    schema_version: "graph-view-model/v1",
    source_schema_version: "ai-system-map/v2",
    project_id: proposal.project_id,
    scan_id: "scan:s1",
    build_id: buildId,
    environment_id: "environment:default-static",
    generated_from_build_id: buildId,
    reference_map_version: "1",
    nodes: [],
    edges: [],
    details: {
      evidence_by_id: {}, risk_hints_by_id: {}, reference_assessments_by_id: {},
      profile_findings_by_id: {}, capability_candidates_by_id: {},
    },
    filters: { available: [], lenses: [] },
  };
  return mapBuildScopedResponseSchema.parse({
    project_id: proposal.project_id,
    scan_id: "scan:s1",
    build_id: buildId,
    based_on_build_id: baseBuildId,
    build_reason: "apply_confirmations",
    applied_mapping_ids: ["mapping:m1"],
    build_result: {
      status: "ok",
      project_name: "demo",
      active_schema_version: "ai-system-map/v2",
      requested_schema_version: "ai-system-map/v2",
      source_schema_version: "ai-system-map/v2",
      operator_rollback_active: false,
      migration_warnings: [],
      warnings: [],
      profile_signals_available: false,
      readiness_report_available: false,
      profile_inference_result: null,
      readiness_report: null,
    },
    viewer_load_result: {
      loaded: true,
      error_reason: null,
      ai_system_map: map,
      graph_view_model: graph,
    },
  });
}

function decisionResult(decision: "confirmed" | "rejected" | "skip_for_now"): MappingProposalDecisionResult {
  const status = decision === "confirmed" ? "accepted" : decision === "rejected" ? "rejected" : "skipped";
  return mappingProposalDecisionResultSchema.parse({
    proposal: { ...proposalSample, status },
    manual_mapping: {
      project_id: proposal.project_id,
      mapping_type: decision === "confirmed" ? "non_baseline_capability_candidate" : "existing_slot_mapping",
      decision,
      source_unmapped_id: proposal.source_unmapped_id,
      evidence_ids: proposal.evidence_packet.evidence_ids,
      ...(decision === "confirmed" ? {
        capability_candidate_id: "capability-candidate:reranker",
        capability_candidate_name: "Reranker",
        capability_candidate_kind: "reranker",
      } : {}),
      mapping_id: "mapping:m1",
      mapping_digest: "digest:m1",
      created_at: "2026-07-21T00:00:00Z",
      updated_at: "2026-07-21T00:00:00Z",
    },
  });
}

function setup() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } });
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useMappingProposal", () => {
  beforeEach(() => {
    vi.mocked(listMappingProposals).mockResolvedValue({
      project_id: proposal.project_id,
      proposals: [proposal],
      available_actions: ["accept", "edit", "reject", "skip_for_now"],
    });
  });

  it("saves a confirmed decision before applying it as a new build", async () => {
    vi.mocked(decideMappingProposal).mockResolvedValue(decisionResult("confirmed"));
    vi.mocked(applyConfirmedMappings).mockResolvedValue(buildResponse("build:b1", "build:b2"));
    const { client, wrapper } = setup();
    const { result } = renderHook(
      () => useMappingProposal("http://api", proposal.project_id, "build:b1"),
      { wrapper },
    );

    act(() => result.current.load({ sourceUnmappedId: proposal.source_unmapped_id }));
    await waitFor(() => expect(result.current.proposal?.proposal_id).toBe(proposal.proposal_id));
    act(() => result.current.decide(proposal, { decision: "accept", candidate_id: proposal.candidates[0].candidate_id }));

    await waitFor(() => expect(result.current.appliedBuild?.build_id).toBe("build:b2"));
    expect(vi.mocked(decideMappingProposal).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(applyConfirmedMappings).mock.invocationCallOrder[0],
    );
    expect(applyConfirmedMappings).toHaveBeenCalledWith("http://api", "build:b1", ["mapping:m1"]);
    expect(client.getQueryData(["viewer-load-result", "api", "http://api", proposal.project_id, null])).toMatchObject({
      viewer_load_result: { build_id: "build:b2" },
    });
  });

  it("keeps reject and skip decisions durable without applying them", async () => {
    vi.mocked(decideMappingProposal).mockResolvedValue(decisionResult("rejected"));
    const { wrapper } = setup();
    const { result } = renderHook(
      () => useMappingProposal("http://api", proposal.project_id, "build:b1"),
      { wrapper },
    );
    act(() => result.current.load({ sourceUnmappedId: proposal.source_unmapped_id }));
    await waitFor(() => expect(result.current.proposal).toBeDefined());
    act(() => result.current.decide(proposal, { decision: "reject", reason: "No evidence-backed fit" }));
    await waitFor(() => expect(result.current.decision?.manual_mapping.decision).toBe("rejected"));
    expect(applyConfirmedMappings).not.toHaveBeenCalled();
  });

  it("requires a latest-build reload after base_build_not_latest and preserves the saved decision", async () => {
    vi.mocked(decideMappingProposal).mockResolvedValue(decisionResult("confirmed"));
    vi.mocked(applyConfirmedMappings)
      .mockRejectedValueOnce(new ApiRequestError("base_build_not_latest", 409))
      .mockResolvedValueOnce(buildResponse("build:b9", "build:b10"));
    const latest = buildResponse("build:b8", "build:b9");
    vi.mocked(loadLatestMapBuild).mockResolvedValue({ response: latest, payload: parseMapBuildPayload(latest) });
    const { wrapper } = setup();
    const { result } = renderHook(
      () => useMappingProposal("http://api", proposal.project_id, "build:b1"),
      { wrapper },
    );

    act(() => result.current.load({ sourceUnmappedId: proposal.source_unmapped_id }));
    await waitFor(() => expect(result.current.proposal).toBeDefined());
    act(() => result.current.decide(proposal, { decision: "accept", candidate_id: proposal.candidates[0].candidate_id }));
    await waitFor(() => expect(result.current.isStaleBuild).toBe(true));
    expect(result.current.pendingMappingId).toBe("mapping:m1");

    act(() => result.current.reloadLatest());
    await waitFor(() => expect(result.current.effectiveBuildId).toBe("build:b9"));
    act(() => result.current.retryApply());
    await waitFor(() => expect(result.current.appliedBuild?.build_id).toBe("build:b10"));
    expect(applyConfirmedMappings).toHaveBeenLastCalledWith("http://api", "build:b9", ["mapping:m1"]);
  });
});
