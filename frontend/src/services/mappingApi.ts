import {
  mappingProposalDecisionResultSchema,
  mappingProposalListResponseSchema,
  mappingProposalSchema,
  type MappingProposal,
  type MappingProposalDecisionResult,
  type MappingProposalListResponse,
  type ProposalDecision,
} from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type MappingProposalScope = {
  projectId: string;
};

function scopeQuery(scope: MappingProposalScope) {
  return new URLSearchParams({
    project_id: scope.projectId,
  }).toString();
}

function assertProjectScope(projectId: string, scope: MappingProposalScope) {
  if (projectId !== scope.projectId) {
    throw new Error("Mapping proposal response does not match the active project.");
  }
}

export async function listMappingProposals(
  baseUrl: string,
  scope: MappingProposalScope,
  signal?: AbortSignal,
): Promise<MappingProposalListResponse> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/mapping-proposals?${scopeQuery(scope)}`;
  const response = mappingProposalListResponseSchema.parse(await fetchJson(url, { signal }));
  assertProjectScope(response.project_id, scope);
  return response;
}

export async function createMappingProposal(
  baseUrl: string,
  scope: MappingProposalScope,
  sourceUnmappedId: string,
  userDescription?: string,
  signal?: AbortSignal,
): Promise<MappingProposal> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/mapping-proposals`;
  const response = mappingProposalSchema.parse(
    await fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: scope.projectId,
        source_unmapped_id: sourceUnmappedId,
        ...(userDescription ? { user_description: userDescription } : {}),
      }),
      signal,
    }),
  );
  assertProjectScope(response.project_id, scope);
  if (response.source_unmapped_id !== sourceUnmappedId) {
    throw new Error("Mapping proposal response does not match the requested component.");
  }
  return response;
}

export async function decideMappingProposal(
  baseUrl: string,
  scope: MappingProposalScope,
  proposalId: string,
  decision: ProposalDecision,
): Promise<MappingProposalDecisionResult> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/mapping-proposals/${encodeURIComponent(proposalId)}/decision`;
  const response = mappingProposalDecisionResultSchema.parse(
    await fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(decision),
    }),
  );
  assertProjectScope(response.proposal.project_id, scope);
  assertProjectScope(response.manual_mapping.project_id, scope);
  if (response.proposal.proposal_id !== proposalId) {
    throw new Error("Mapping decision response does not match the requested proposal.");
  }
  return response;
}
