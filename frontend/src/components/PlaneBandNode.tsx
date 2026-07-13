import type { NodeProps } from "reactflow";
import { getPlaneIcon } from "../icons/registry";

export type PlaneBandData = {
  planeId: string;
  label: string;
  sublabel: string | null;
  count: number;
};

/* Visual chrome only: a band backdrop for one backend-declared plane. It is
   never selectable and never carries graph semantics. The head icon comes from
   the plane registry; unknown planes and the unassigned band render none. */
export function PlaneBandNode({ data }: NodeProps<PlaneBandData>) {
  const PlaneIcon = getPlaneIcon(data.planeId);
  return (
    <div className="plane-band" aria-hidden="true">
      <div className="plane-band-head">
        {PlaneIcon ? <PlaneIcon className="plane-band-ico" size={13} aria-hidden="true" /> : null}
        <strong>{data.label}</strong>
        {data.sublabel ? <em>{data.sublabel}</em> : null}
        <span>{data.count}</span>
      </div>
    </div>
  );
}
