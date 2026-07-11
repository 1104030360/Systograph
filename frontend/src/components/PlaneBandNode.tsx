import type { NodeProps } from "reactflow";

export type PlaneBandData = {
  label: string;
  sublabel: string | null;
  count: number;
};

/* Visual chrome only: a band backdrop for one backend-declared plane. It is
   never selectable and never carries graph semantics. */
export function PlaneBandNode({ data }: NodeProps<PlaneBandData>) {
  return (
    <div className="plane-band" aria-hidden="true">
      <div className="plane-band-head">
        <strong>{data.label}</strong>
        {data.sublabel ? <em>{data.sublabel}</em> : null}
        <span>{data.count}</span>
      </div>
    </div>
  );
}
