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

export async function listMappingProposals(
  baseUrl: string,
  projectId: string,
): Promise<MappingProposalListResponse> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/mapping-proposals?project_id=${encodeURIComponent(projectId)}`;
  return mappingProposalListResponseSchema.parse(await fetchJson(url));
}

export async function createMappingProposal(
  baseUrl: string,
  projectId: string,
  sourceUnmappedId: string,
): Promise<MappingProposal> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/mapping-proposals`;
  return mappingProposalSchema.parse(
    await fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, source_unmapped_id: sourceUnmappedId }),
    }),
  );
}

export async function decideMappingProposal(
  baseUrl: string,
  proposalId: string,
  decision: ProposalDecision,
): Promise<MappingProposalDecisionResult> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/mapping-proposals/${encodeURIComponent(proposalId)}/decision`;
  return mappingProposalDecisionResultSchema.parse(
    await fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(decision),
    }),
  );
}
