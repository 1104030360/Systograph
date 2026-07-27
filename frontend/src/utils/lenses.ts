import type { GraphLensModel } from "../types";

/* Graph Studio ships exactly six lenses (Meeting Sync 2026-07-07). Membership is
   backend-provided projection data; the frontend never derives it from node
   labels, topology, or file names. A lens the payload does not cover renders
   disabled with an explanation instead of guessing. */
export const GRAPH_STUDIO_LENS_KEYS = [
  "data",
  "control",
  "evidence",
  "governance",
  "source",
  "risk",
] as const;

export type GraphStudioLensKey = (typeof GRAPH_STUDIO_LENS_KEYS)[number];

const FALLBACK_LENS_LABELS: Record<GraphStudioLensKey, string> = {
  data: "Data",
  control: "Control",
  evidence: "Evidence",
  governance: "Governance",
  source: "Source",
  risk: "Risk",
};

export const LENS_MEMBERSHIP_MISSING_REASON =
  "Backend projection has not published membership for this lens.";

export type LensAvailability = "available" | "unsupported" | "missing";

export type LensSlotView = {
  /** Canonical key when the lens is one of the six fixed lenses, else the backend id. */
  key: string;
  /** Id used for activation — the backend id when provided, never invented otherwise. */
  id: string | null;
  label: string;
  availability: LensAvailability;
  unavailableReason: string | null;
  matchCount: number;
};

/* Backend lens ids are not finalized in the contract docs (only the six labels
   are); accept "lens:data", "lens_data", "data", or a label match so the UI
   does not silently drop a published lens over id spelling. */
export function canonicalLensKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/^lens[:_-]/, "");
}

function slotFromBackendLens(lens: GraphLensModel, label: string, key: string): LensSlotView {
  const matchCount = lens.matches_node_ids.length + lens.matches_edge_ids.length;
  if (!lens.supported) {
    return {
      key,
      id: lens.id,
      label,
      availability: "unsupported",
      unavailableReason: lens.unavailable_reason ?? LENS_MEMBERSHIP_MISSING_REASON,
      matchCount,
    };
  }
  return {
    key,
    id: lens.id,
    label,
    availability: "available",
    unavailableReason: null,
    matchCount,
  };
}

export function resolveLensSlots(lenses: GraphLensModel[]): LensSlotView[] {
  const byKey = new Map<string, GraphLensModel>();
  lenses.forEach((lens) => {
    const key = canonicalLensKey(lens.id);
    if (!byKey.has(key)) byKey.set(key, lens);
    const labelKey = canonicalLensKey(lens.label);
    if (!byKey.has(labelKey)) byKey.set(labelKey, lens);
  });

  const fixedSlots: LensSlotView[] = GRAPH_STUDIO_LENS_KEYS.map((key) => {
    const lens = byKey.get(key);
    if (!lens) {
      return {
        key,
        id: null,
        label: FALLBACK_LENS_LABELS[key],
        availability: "missing" as const,
        unavailableReason: LENS_MEMBERSHIP_MISSING_REASON,
        matchCount: 0,
      };
    }
    return slotFromBackendLens(lens, lens.label || FALLBACK_LENS_LABELS[key], key);
  });

  const fixedKeys = new Set<string>(GRAPH_STUDIO_LENS_KEYS);
  const extraSlots = lenses
    .filter((lens) => !fixedKeys.has(canonicalLensKey(lens.id)) && !fixedKeys.has(canonicalLensKey(lens.label)))
    .map((lens) => slotFromBackendLens(lens, lens.label || lens.id, canonicalLensKey(lens.id)));

  return [...fixedSlots, ...extraSlots];
}

/* Mirrors getFilterMatches: only a lens that exists in the payload and is
   supported can highlight, so a stale active lens id from a previous build
   cannot dim the entire graph. */
export function getLensMatches(lenses: GraphLensModel[], activeLensId: string | null) {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  const activeLens = activeLensId
    ? lenses.find((lens) => lens.id === activeLensId && lens.supported)
    : undefined;

  activeLens?.matches_node_ids.forEach((id) => nodeIds.add(id));
  activeLens?.matches_edge_ids.forEach((id) => edgeIds.add(id));

  return { nodeIds, edgeIds, hasLens: activeLens != null };
}
