import { z } from "zod";
import { mapBuildScopedResponseSchema, parseMapBuildPayload } from "../contracts/viewer";
import type { ViewerPayload } from "../types";
import { fetchJson, normalizeBaseUrl } from "./http";

export type ApplyConfirmationsResponse = z.infer<typeof mapBuildScopedResponseSchema>;

export async function loadLatestMapBuild(
  baseUrl: string,
  projectId: string,
): Promise<{ response: ApplyConfirmationsResponse; payload: ViewerPayload }> {
  const url = `${normalizeBaseUrl(baseUrl)}/api/projects/${encodeURIComponent(projectId)}/map-builds/latest`;
  const raw = await fetchJson(url);
  return {
    response: mapBuildScopedResponseSchema.parse(raw),
    payload: parseMapBuildPayload(raw),
  };
}

export async function applyConfirmedMappings(
  baseUrl: string,
  baseBuildId: string,
  mappingIds: string[],
): Promise<ApplyConfirmationsResponse> {
  const uniqueMappingIds = [...new Set(mappingIds)];
  if (!uniqueMappingIds.length || uniqueMappingIds.length !== mappingIds.length) {
    throw new Error("Apply requires one or more unique mapping ids.");
  }

  const url = `${normalizeBaseUrl(baseUrl)}/api/map-builds/${encodeURIComponent(baseBuildId)}/apply`;
  const response = mapBuildScopedResponseSchema.parse(
    await fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mapping_ids: uniqueMappingIds }),
    }),
  );

  if (response.build_reason !== "apply_confirmations" || response.based_on_build_id !== baseBuildId) {
    throw new Error("Apply response does not match the requested base build.");
  }
  if (
    response.applied_mapping_ids.length !== uniqueMappingIds.length ||
    !uniqueMappingIds.every((mappingId) => response.applied_mapping_ids.includes(mappingId))
  ) {
    throw new Error("Apply response does not contain the requested mapping decisions.");
  }
  return response;
}
