import { afterEach, describe, expect, it, vi } from "vitest";
import proposalSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-mapping-proposal-sample.json";
import { createMappingProposal, decideMappingProposal, listMappingProposals } from "./mappingApi";

const scope = { projectId: proposalSample.project_id };

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function confirmedDecision() {
  return {
    proposal: { ...proposalSample, status: "accepted" },
    manual_mapping: {
      project_id: proposalSample.project_id,
      mapping_type: "non_baseline_capability_candidate",
      decision: "confirmed",
      source_unmapped_id: proposalSample.source_unmapped_id,
      evidence_ids: proposalSample.evidence_packet.evidence_ids,
      capability_candidate_id: "capability-candidate:reranker",
      capability_candidate_name: "Reranker",
      capability_candidate_kind: "reranker",
      mapping_id: "mapping:m1",
      mapping_digest: "digest:m1",
      created_at: "2026-07-21T00:00:00Z",
      updated_at: "2026-07-21T00:00:00Z",
    },
  };
}

describe("mapping proposal API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the backend's current project-level proposal routes", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ project_id: scope.projectId, proposals: [proposalSample] }))
      .mockResolvedValueOnce(jsonResponse(proposalSample));
    vi.stubGlobal("fetch", fetchMock);

    await listMappingProposals("http://127.0.0.1:8000/", scope);
    await createMappingProposal("http://127.0.0.1:8000/", scope, proposalSample.source_unmapped_id);

    expect(String(fetchMock.mock.calls[0][0])).toContain(
      `/api/mapping-proposals?project_id=${encodeURIComponent(scope.projectId)}`,
    );
    expect(String(fetchMock.mock.calls[0][0])).not.toContain("build_id=");
    expect(String(fetchMock.mock.calls[1][0])).toBe("http://127.0.0.1:8000/api/mapping-proposals");
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      project_id: scope.projectId,
      source_unmapped_id: proposalSample.source_unmapped_id,
    });
  });

  it("sends a proposal-id decision and parses its durable mapping", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(confirmedDecision()));
    vi.stubGlobal("fetch", fetchMock);

    const result = await decideMappingProposal(
      "http://127.0.0.1:8000",
      scope,
      proposalSample.proposal_id,
      { decision: "accept", candidate_id: proposalSample.candidates[0].candidate_id },
    );

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      `http://127.0.0.1:8000/api/mapping-proposals/${encodeURIComponent(proposalSample.proposal_id)}/decision`,
    );
    expect(result.manual_mapping.mapping_id).toBe("mapping:m1");
  });

  it("rejects a response from another project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      project_id: "project:other",
      proposals: [],
    })));
    await expect(listMappingProposals("http://127.0.0.1:8000", scope)).rejects.toThrow(/active project/);
  });
});
