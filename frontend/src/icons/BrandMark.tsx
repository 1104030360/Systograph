import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement> & { size?: number };

/* Product mark migrated from the DeepResearch mock's node-graph glyph
   (see docs/work/Hardy/2026-07-13-deepresearch-icon-inventory.md). Redrawn as
   a single-color SVG: strokes and node dots both use currentColor so the mark
   inherits whatever token its container sets — no mock palette. */
export function BrandMark({ size = 17, ...props }: Props) {
  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path d="M7 16h18M16 7v18M9.5 9.5l13 13M22.5 9.5l-13 13" />
      <circle cx="7" cy="16" r="3.5" fill="currentColor" stroke="none" />
      <circle cx="25" cy="16" r="3.5" fill="currentColor" stroke="none" />
      <circle cx="16" cy="7" r="3.5" fill="currentColor" stroke="none" />
      <circle cx="16" cy="25" r="3.5" fill="currentColor" stroke="none" />
    </svg>
  );
}
