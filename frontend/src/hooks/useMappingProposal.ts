import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createMappingProposal, decideMappingProposal, listMappingProposals } from "../services/mappingApi";
import { loadApiViewerPayload } from "../services/viewerApi";
import type { MappingProposal, MappingProposalDecisionResult } from "../types";

type Target = { projectId: string; sourceUnmappedId: string };
type DecisionInput =
  | { proposal: MappingProposal; decision: "accept"; candidateId: string }
  | { proposal: MappingProposal; decision: "reject"; reason?: string };

export type MappingDecisionResult = {
  result: MappingProposalDecisionResult;
  refreshWarning?: string;
};

export function useMappingProposal(apiBaseUrl: string) {
  const queryClient = useQueryClient();
  const loadMutation = useMutation({
    mutationFn: async ({ projectId, sourceUnmappedId }: Target) => {
      const listed = await listMappingProposals(apiBaseUrl, projectId);
      const pending = listed.proposals.find(
        (proposal) =>
          proposal.source_unmapped_id === sourceUnmappedId &&
          proposal.status === "pending_user_confirmation",
      );
      return pending ?? createMappingProposal(apiBaseUrl, projectId, sourceUnmappedId);
    },
  });

  const decisionMutation = useMutation({
    mutationFn: async (input: DecisionInput): Promise<MappingDecisionResult> => {
      const decision =
        input.decision === "accept"
          ? { decision: "accept" as const, candidate_id: input.candidateId }
          : { decision: "reject" as const, reason: input.reason };
      const result = await decideMappingProposal(apiBaseUrl, input.proposal.proposal_id, decision);

      if (input.decision === "reject") return { result };
      try {
        const refreshedPayload = await loadApiViewerPayload(apiBaseUrl);
        queryClient.setQueryData(["viewer-load-result", "api", apiBaseUrl], refreshedPayload);
        return { result };
      } catch (error) {
        return {
          result,
          refreshWarning:
            error instanceof Error
              ? `Mapping saved, but the map could not be refreshed: ${error.message}`
              : "Mapping saved, but the map could not be refreshed.",
        };
      }
    },
  });

  return {
    load: loadMutation.mutate,
    proposal: loadMutation.data,
    loadError: loadMutation.error instanceof Error ? loadMutation.error.message : undefined,
    isLoading: loadMutation.isPending,
    decide: decisionMutation.mutate,
    decision: decisionMutation.data,
    decisionError: decisionMutation.error instanceof Error ? decisionMutation.error.message : undefined,
    isDeciding: decisionMutation.isPending,
    reset: () => {
      loadMutation.reset();
      decisionMutation.reset();
    },
  };
}
