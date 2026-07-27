import type { CSSProperties, HTMLAttributes } from "react";
import {
  Activity,
  ArrowRightLeft,
  BrainCircuit,
  CircleDot,
  Database,
  FileCode2,
  GitBranch,
  Network,
  PackageOpen,
  Puzzle,
  ScanLine,
  Search,
  ShieldCheck,
  SquareCheckBig,
  TriangleAlert,
  Workflow,
  type LucideIcon,
} from "lucide-react";

export type PrototypeIconKind =
  | "overview"
  | "data"
  | "control"
  | "ingestion"
  | "retrieval"
  | "memory"
  | "governance"
  | "runtime"
  | "variant"
  | "risk"
  | "known"
  | "extension"
  | "unmapped"
  | "mode"
  | "topology"
  | "source";

type Props = Omit<HTMLAttributes<HTMLSpanElement>, "children"> & {
  kind: PrototypeIconKind;
  size?: number;
};

const GLYPHS: Record<PrototypeIconKind, LucideIcon> = {
  overview: CircleDot,
  data: ArrowRightLeft,
  control: Workflow,
  ingestion: PackageOpen,
  retrieval: Search,
  memory: Database,
  governance: ShieldCheck,
  runtime: Activity,
  variant: GitBranch,
  risk: TriangleAlert,
  known: SquareCheckBig,
  extension: Puzzle,
  unmapped: ScanLine,
  mode: BrainCircuit,
  topology: Network,
  source: FileCode2,
};

/** Scalable semantic glyphs inside the prototype's color-coded icon tile. */
export function PrototypeIcon({ kind, size = 30, className, style, ...props }: Props) {
  const Glyph = GLYPHS[kind];
  const glyphSize = Math.max(12, Math.round(size * 0.62));

  return (
    <span
      className={["prototype-icon", `prototype-icon-${kind}`, className].filter(Boolean).join(" ")}
      style={{ "--prototype-icon-size": `${size}px`, ...style } as CSSProperties}
      aria-hidden="true"
      {...props}
    >
      <Glyph size={glyphSize} strokeWidth={1.9} focusable="false" />
    </span>
  );
}
