import {
  AlertTriangle,
  ArrowRightLeft,
  Code,
  Database,
  FileInput,
  FileSearch,
  MessageSquareText,
  Network,
  Puzzle,
  Search,
  ShieldCheck,
  Sparkles,
  Telescope,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { canonicalLensKey, type GraphStudioLensKey } from "../utils/lenses";
import { UNASSIGNED_PLANE_ID } from "../utils/planes";

/* Single icon mapping for the semantics the DeepResearch mock expressed with
   custom glyphs (source-to-target inventory:
   docs/work/Hardy/2026-07-13-deepresearch-icon-inventory.md). Generic actions
   keep importing lucide directly in their components; the brand mark lives in
   ./BrandMark.tsx as a component-only module. */

export const LENS_ICONS = {
  data: ArrowRightLeft,
  control: Workflow,
  evidence: FileSearch,
  governance: ShieldCheck,
  source: Code,
  risk: AlertTriangle,
} satisfies Record<GraphStudioLensKey, LucideIcon>;

/* Accepts either a fixed lens key or a backend lens id ("lens:data" et al).
   Extra backend lenses beyond the fixed six get the generic lens glyph. */
export function getLensIcon(lensKeyOrId: string): LucideIcon {
  const key = canonicalLensKey(lensKeyOrId);
  return key in LENS_ICONS ? LENS_ICONS[key as GraphStudioLensKey] : Telescope;
}

/* Keyed by the backend plane ids (utils/planes.ts PLANE_PRESENTATION_ORDER).
   An unknown plane id — including the synthetic unassigned band — yields
   undefined: callers render no icon instead of inferring one, mirroring how
   layoutPlaneBands never guesses plane membership. */
export const PLANE_ICONS: Record<string, LucideIcon> = {
  input_intent: MessageSquareText,
  control: Workflow,
  ingestion_indexing: FileInput,
  retrieval: Search,
  extension_subsystems: Puzzle,
  evidence: FileSearch,
  generation: Sparkles,
  memory_state: Database,
  governance_observability: ShieldCheck,
  deployment_topology: Network,
};

export function getPlaneIcon(planeId: string | null | undefined): LucideIcon | undefined {
  if (!planeId || planeId === UNASSIGNED_PLANE_ID) return undefined;
  return PLANE_ICONS[planeId];
}
