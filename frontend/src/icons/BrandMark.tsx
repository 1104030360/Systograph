import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement> & { size?: number };

/* Exact multicolour node-graph mark from DeepResearch/index.html. */
export function BrandMark({ size = 17, ...props }: Props) {
  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path
        d="M7 16h18M16 7v18M9.5 9.5l13 13M22.5 9.5l-13 13"
        stroke="#256ee8"
        strokeWidth={2}
        strokeLinecap="round"
      />
      <circle cx="7" cy="16" r="3.5" fill="#22b35d" />
      <circle cx="25" cy="16" r="3.5" fill="#ff9f1c" />
      <circle cx="16" cy="7" r="3.5" fill="#8a45d7" />
      <circle cx="16" cy="25" r="3.5" fill="#256ee8" />
    </svg>
  );
}
