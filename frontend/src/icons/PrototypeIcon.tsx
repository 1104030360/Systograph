import type { CSSProperties, HTMLAttributes } from "react";

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

/** CSS-drawn icon primitives copied from the DeepResearch prototype. */
export function PrototypeIcon({ kind, size = 30, className, style, ...props }: Props) {
  return (
    <span
      className={["prototype-icon", `prototype-icon-${kind}`, className].filter(Boolean).join(" ")}
      style={{ "--prototype-icon-size": `${size}px`, ...style } as CSSProperties}
      aria-hidden="true"
      {...props}
    />
  );
}
