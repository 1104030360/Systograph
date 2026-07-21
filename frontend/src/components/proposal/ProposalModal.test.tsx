import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import proposalSample from "../../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-mapping-proposal-sample.json";
import { useMappingProposal } from "../../hooks/useMappingProposal";
import { mappingProposalSchema } from "../../types";
import { ProposalModal } from "./ProposalModal";

vi.mock("../../hooks/useMappingProposal", () => ({ useMappingProposal: vi.fn() }));

const proposal = mappingProposalSchema.parse(proposalSample);
const node = {
  unmapped_id: proposal.source_unmapped_id,
  node_path: proposal.evidence_packet.source_file ?? "src/pipeline.py",
  node_kind: proposal.evidence_packet.observed_kind,
};

function hookState(overrides: Partial<ReturnType<typeof useMappingProposal>> = {}): ReturnType<typeof useMappingProposal> {
  return {
    load: vi.fn(),
    proposal,
    decision: null,
    appliedBuild: undefined,
    effectiveBuildId: "build:b1",
    pendingMappingId: null,
    isLoading: false,
    isDeciding: false,
    isApplying: false,
    isReloadingLatest: false,
    isStaleBuild: false,
    isConflicted: false,
    loadError: undefined,
    decisionError: undefined,
    applyError: undefined,
    reloadLatestError: undefined,
    decide: vi.fn(),
    retryLoad: vi.fn(),
    retryApply: vi.fn(),
    reloadLatest: vi.fn(),
    reset: vi.fn(),
    ...overrides,
  };
}

function renderApiModal() {
  return render(
    <ProposalModal
      node={node}
      apiBaseUrl="http://api"
      projectId={proposal.project_id}
      buildId="build:b1"
      onClose={() => {}}
    />,
  );
}

describe("ProposalModal v2", () => {
  beforeEach(() => vi.mocked(useMappingProposal).mockReturnValue(hookState()));

  it("presents non-baseline candidates as review signals, not detected map components", () => {
    renderApiModal();
    expect(screen.getByText(/capability signal, not a detected component/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit/i })).toBeInTheDocument();
    expect(screen.getAllByText("evidence:reranker-call").length).toBeGreaterThan(0);
  });

  it("submits edits with only backend-provided targets", () => {
    const decide = vi.fn();
    const editableProposal = {
      ...proposal,
      evidence_packet: { ...proposal.evidence_packet, available_slots: ["retriever", "llm"] },
      candidates: [{
        ...proposal.candidates[0],
        candidate_type: "existing_slot_mapping" as const,
        target_slot: "retriever",
        component_name: "Detected retriever",
        component_kind: "retrieval",
        proposed_capability_candidate_id: null,
        proposed_capability_candidate_name: null,
        proposed_capability_candidate_kind: null,
      }],
    };
    vi.mocked(useMappingProposal).mockReturnValue(hookState({ proposal: editableProposal, decide }));
    renderApiModal();

    fireEvent.click(screen.getByRole("button", { name: /^Edit$/i }));
    expect(screen.getByRole("option", { name: "retriever" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "llm" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Component name"), { target: { value: "Reviewed retriever" } });
    fireEvent.click(screen.getByRole("button", { name: /Submit edited mapping/i }));

    expect(decide).toHaveBeenCalledWith(editableProposal, expect.objectContaining({
      decision: "edit",
      edited_mapping: expect.objectContaining({
        project_id: proposal.project_id,
        source_unmapped_id: proposal.source_unmapped_id,
        target_slot: "retriever",
        component_name: "Reviewed retriever",
      }),
    }));
  });

  it("renders only masked evidence summaries", () => {
    const maskedProposal = {
      ...proposal,
      evidence_packet: {
        ...proposal.evidence_packet,
        masked_snippets: ["api_key=[REDACTED]"],
      },
    };
    vi.mocked(useMappingProposal).mockReturnValue(hookState({ proposal: maskedProposal }));
    renderApiModal();
    expect(screen.getAllByText("api_key=[REDACTED]").length).toBeGreaterThan(0);
    expect(screen.queryByText(/sk-live-/i)).not.toBeInTheDocument();
  });

  it("keeps needs_more_information read-only", () => {
    const needsInformation = {
      ...proposal,
      candidates: [{
        ...proposal.candidates[0],
        candidate_id: "candidate:more",
        candidate_type: "needs_more_information" as const,
        target_slot: null,
        proposed_capability_candidate_id: null,
        proposed_capability_candidate_name: null,
        proposed_capability_candidate_kind: null,
        label: "Needs more information",
      }],
    };
    vi.mocked(useMappingProposal).mockReturnValue(hookState({ proposal: needsInformation }));
    renderApiModal();

    expect(screen.getByText(/Keep this item unknown/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Confirm$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Edit$/i })).not.toBeInTheDocument();
  });

  it("turns skip_for_now candidates into a durable skip decision", () => {
    const decide = vi.fn();
    const skipProposal = { ...proposal, candidates: [proposal.candidates[1]] };
    vi.mocked(useMappingProposal).mockReturnValue(hookState({ proposal: skipProposal, decide }));
    renderApiModal();
    fireEvent.click(screen.getAllByRole("button", { name: /Skip for now/i })[0]);
    expect(decide).toHaveBeenCalledWith(skipProposal, { decision: "skip_for_now" });
  });

  it("requires an explicit latest-build reload for stale apply", () => {
    const reloadLatest = vi.fn();
    vi.mocked(useMappingProposal).mockReturnValue(hookState({
      decision: {
        proposal: { ...proposal, status: "accepted" },
        manual_mapping: {
          project_id: proposal.project_id,
          mapping_type: "non_baseline_capability_candidate",
          decision: "confirmed",
          source_unmapped_id: proposal.source_unmapped_id,
          evidence_ids: proposal.evidence_packet.evidence_ids,
          capability_candidate_id: "capability-candidate:reranker",
          capability_candidate_name: "Reranker",
          capability_candidate_kind: "reranker",
          mapping_id: "mapping:m1",
          mapping_digest: "digest:m1",
          created_at: "2026-07-21T00:00:00Z",
          updated_at: "2026-07-21T00:00:00Z",
        },
      },
      pendingMappingId: "mapping:m1",
      isStaleBuild: true,
      applyError: "base_build_not_latest",
      reloadLatest,
    }));
    renderApiModal();

    expect(screen.getByRole("heading", { name: /Base build is stale/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Reload latest build/i }));
    expect(reloadLatest).toHaveBeenCalledOnce();
  });

  it("shows finalized proposal conflicts instead of allowing a second decision", () => {
    vi.mocked(useMappingProposal).mockReturnValue(hookState({
      proposal: { ...proposal, status: "rejected" },
      isConflicted: true,
    }));
    renderApiModal();
    expect(screen.getByRole("heading", { name: /Proposal state conflicted/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Confirm$/i })).not.toBeInTheDocument();
  });
});
