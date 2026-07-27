import { describe, expect, it } from "vitest";
import proposalSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-mapping-proposal-sample.json";
import {
  mappingCandidateSchema,
  mappingProposalDecisionResultSchema,
  mappingProposalSchema,
} from "../types";

describe("current mapping proposal contract", () => {
  it("parses the Timmy v2 proposal handoff without inventing a detected component", () => {
    const proposal = mappingProposalSchema.parse(proposalSample);

    expect(proposal.candidates.map((candidate) => candidate.candidate_type)).toEqual([
      "non_baseline_capability_candidate",
      "skip_for_now",
    ]);
    expect(proposal.candidates[0].target_slot).toBeNull();
    expect(proposal.evidence_packet.evidence_ids).toEqual(["evidence:reranker-call"]);
  });

  it.each(["new_" + "extension_component", "ui_" + "extension"])("rejects retired candidate type %s", (candidateType) => {
    const candidate = structuredClone(proposalSample.candidates[0]) as Record<string, unknown>;
    candidate.candidate_type = candidateType;
    expect(mappingCandidateSchema.safeParse(candidate).success).toBe(false);
  });

  it("requires a durable manual mapping for skip decisions", () => {
    const skipped = {
      proposal: { ...proposalSample, status: "skipped" },
      manual_mapping: {
        project_id: proposalSample.project_id,
        mapping_type: "existing_slot_mapping",
        decision: "skip_for_now",
        source_unmapped_id: proposalSample.source_unmapped_id,
        evidence_ids: proposalSample.evidence_packet.evidence_ids,
        mapping_id: "mapping:skip",
        mapping_digest: "digest:skip",
        created_at: "2026-07-21T00:00:00Z",
        updated_at: "2026-07-21T00:00:00Z",
      },
    };

    expect(mappingProposalDecisionResultSchema.parse(skipped).manual_mapping.decision).toBe("skip_for_now");
    expect(
      mappingProposalDecisionResultSchema.safeParse({ ...skipped, manual_mapping: null }).success,
    ).toBe(false);
  });
});
