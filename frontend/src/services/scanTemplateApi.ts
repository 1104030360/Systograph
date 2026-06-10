/* ============================================================================
   scanTemplateApi — service seam for the Scan Template / Mapping Profile page.

   The Scan-Template / project-custom-version selection API does NOT exist yet,
   so every call resolves from the typed mock in data/scanTemplate.mock.ts.
   This is the single swap point: when the backend ships, replace the bodies
   with `fetch('/api/scan-templates?project_id=…')` etc. — no component changes
   required, because the return shapes already match src/types.ts.
   ========================================================================== */
import {
  CONFIRMED,
  PENDING,
  PROJECT,
  PROJECT_CUSTOM,
  SELECTED_PROFILE_ID,
  SKIPPED,
  SYSTEM_DEFAULT,
} from "../data/scanTemplate.mock";
import type {
  ConfirmedMappingRow,
  PendingProposalRow,
  ScanProfile,
  ScanTemplateState,
  SkippedDecisionRow,
} from "../types";

/** Simulate the latency of a local round-trip so loading states are visible. */
const NETWORK_MS = 420;
const delay = <T>(value: T, ms = NETWORK_MS): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

export interface MappingStatusLists {
  confirmed: ConfirmedMappingRow[];
  pending: PendingProposalRow[];
  skipped: SkippedDecisionRow[];
}

export const scanTemplateApi = {
  /** Full template state for a project: profiles + which one the next scan uses. */
  async getState(_projectId: string = PROJECT.project_id): Promise<ScanTemplateState> {
    const profiles: ScanProfile[] = [SYSTEM_DEFAULT];
    // PROJECT_CUSTOM is non-null in the mock; set to skip it to exercise the
    // empty-state branch in ProjectCustomCard.
    if (PROJECT_CUSTOM) profiles.push(PROJECT_CUSTOM);
    return delay({
      project_id: PROJECT.project_id,
      project_name: PROJECT.project_name,
      selected_profile_id: SELECTED_PROFILE_ID,
      profiles,
    });
  },

  /** The three mapping-status lists shown under the overview cards. */
  async listMappingStatus(_projectId: string = PROJECT.project_id): Promise<MappingStatusLists> {
    return delay({ confirmed: CONFIRMED, pending: PENDING, skipped: SKIPPED });
  },

  /** Select which profile the next scan should use. Real impl: PUT. */
  async select(profileId: string, _projectId: string = PROJECT.project_id): Promise<{ selected_profile_id: string }> {
    return delay({ selected_profile_id: profileId }, 200);
  },
};
