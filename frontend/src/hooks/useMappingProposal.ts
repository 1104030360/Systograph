import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { parseMapBuildPayload } from "../contracts/viewer";
import { applyConfirmedMappings, loadLatestMapBuild } from "../services/mapBuildApi";
import {
  createMappingProposal,
  decideMappingProposal,
  listMappingProposals,
  type MappingProposalScope,
} from "../services/mappingApi";
import { ApiRequestError } from "../services/http";
import type {
  MappingProposal,
  MappingProposalDecisionResult,
  ProposalDecision,
} from "../types";

type LoadInput = { sourceUnmappedId: string; userDescription?: string };

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function useMappingProposal(
  apiBaseUrl: string,
  projectId: string,
  buildId: string,
) {
  const queryClient = useQueryClient();
  const [effectiveBuildId, setEffectiveBuildId] = useState(buildId);
  const [decision, setDecision] = useState<MappingProposalDecisionResult | null>(null);
  const [pendingMappingId, setPendingMappingId] = useState<string | null>(null);

  useEffect(() => {
    setEffectiveBuildId(buildId);
    setDecision(null);
    setPendingMappingId(null);
  }, [buildId, projectId]);

  // Proposal lifecycle is project-level in the current backend. buildId is
  // retained only as the immutable base for the separately scoped Apply API.
  const scope: MappingProposalScope = { projectId };

  const loadMutation = useMutation({
    mutationFn: async ({ sourceUnmappedId, userDescription }: LoadInput) => {
      const listed = await listMappingProposals(apiBaseUrl, scope);
      const matches = listed.proposals.filter(
        (proposal) => proposal.source_unmapped_id === sourceUnmappedId,
      );
      const pending = matches.find(
        (proposal) => proposal.status === "pending_user_confirmation",
      );
      return (
        pending ??
        matches[0] ??
        createMappingProposal(apiBaseUrl, scope, sourceUnmappedId, userDescription)
      );
    },
  });

  const applyMutation = useMutation({
    mutationFn: ({ mappingId, baseBuildId }: { mappingId: string; baseBuildId: string }) =>
      applyConfirmedMappings(apiBaseUrl, baseBuildId, [mappingId]),
    onSuccess: (response) => {
      const payload = parseMapBuildPayload(response);
      queryClient.setQueryData(
        ["viewer-load-result", "api", apiBaseUrl, projectId, null],
        payload,
      );
      void queryClient.invalidateQueries({ queryKey: ["map-builds", apiBaseUrl, projectId] });
      setEffectiveBuildId(response.build_id);
      setPendingMappingId(null);
    },
  });

  const decisionMutation = useMutation({
    mutationFn: ({ proposal, request }: { proposal: MappingProposal; request: ProposalDecision }) =>
      decideMappingProposal(apiBaseUrl, scope, proposal.proposal_id, request),
    onSuccess: (result) => {
      setDecision(result);
      if (result.manual_mapping.decision !== "confirmed") {
        setPendingMappingId(null);
        return;
      }
      const mappingId = result.manual_mapping.mapping_id;
      setPendingMappingId(mappingId);
      applyMutation.mutate({ mappingId, baseBuildId: effectiveBuildId });
    },
  });

  const reloadLatestMutation = useMutation({
    mutationFn: () => loadLatestMapBuild(apiBaseUrl, projectId),
    onSuccess: ({ response, payload }) => {
      queryClient.setQueryData(
        ["viewer-load-result", "api", apiBaseUrl, projectId, null],
        payload,
      );
      setEffectiveBuildId(response.build_id);
      applyMutation.reset();
    },
  });

  const applyError = applyMutation.error;
  const isStaleBuild =
    applyError instanceof ApiRequestError &&
    applyError.status === 409 &&
    applyError.message === "base_build_not_latest";
  const proposal = loadMutation.data;
  const isConflicted = Boolean(
    proposal && proposal.status !== "pending_user_confirmation" && !decision,
  );

  return {
    load: loadMutation.mutate,
    proposal,
    decision,
    appliedBuild: applyMutation.data,
    effectiveBuildId,
    pendingMappingId,
    isLoading: loadMutation.isPending,
    isDeciding: decisionMutation.isPending,
    isApplying: applyMutation.isPending,
    isReloadingLatest: reloadLatestMutation.isPending,
    isStaleBuild,
    isConflicted,
    loadError: loadMutation.error ? errorMessage(loadMutation.error) : undefined,
    decisionError: decisionMutation.error ? errorMessage(decisionMutation.error) : undefined,
    applyError: applyError ? errorMessage(applyError) : undefined,
    reloadLatestError: reloadLatestMutation.error
      ? errorMessage(reloadLatestMutation.error)
      : undefined,
    decide: (proposalToDecide: MappingProposal, request: ProposalDecision) =>
      decisionMutation.mutate({ proposal: proposalToDecide, request }),
    retryLoad: () => {
      const sourceUnmappedId = proposal?.source_unmapped_id;
      loadMutation.reset();
      if (sourceUnmappedId) loadMutation.mutate({ sourceUnmappedId });
    },
    retryApply: () => {
      if (pendingMappingId) {
        applyMutation.reset();
        applyMutation.mutate({ mappingId: pendingMappingId, baseBuildId: effectiveBuildId });
      }
    },
    reloadLatest: reloadLatestMutation.mutate,
    reset: () => {
      loadMutation.reset();
      decisionMutation.reset();
      applyMutation.reset();
      reloadLatestMutation.reset();
      setDecision(null);
      setPendingMappingId(null);
      setEffectiveBuildId(buildId);
    },
  };
}
