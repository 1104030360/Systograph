import { Handle, Position, type NodeProps } from "reactflow";
import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
import type { FlowNodeData } from "../utils/graph";

export function SystemNode({ data }: NodeProps<FlowNodeData>) {
  const hasRisk = data.risk_hint_ids.length > 0;
  const needsConfirmation = data.status?.includes("confirmation") || data.badges.includes("needs_confirmation");
  const detected = data.status === "detected" || data.badges.includes("detected");

  return (
    <div
      className={[
        "system-node",
        data.isFocused ? "is-focused" : "",
        data.isDimmed ? "is-dimmed" : "",
        data.isSelected ? "is-selected" : "",
        data.isProgressTarget ? "is-progress" : "",
        hasRisk ? "has-risk" : "",
      ].join(" ")}
    >
      <Handle className="node-handle input" position={Position.Left} type="target" />
      <div className="node-topline">
        <span className="node-type">{data.subtitle ?? data.slot ?? data.type}</span>
        {hasRisk ? <AlertTriangle size={15} /> : needsConfirmation ? <CircleDashed size={15} /> : detected ? <CheckCircle2 size={15} /> : null}
      </div>
      <div className="node-title">{data.label}</div>
      <div className="node-meta">
        {data.badges.slice(0, 3).map((badge) => (
          <span className="node-badge" key={badge}>
            {badge}
          </span>
        ))}
      </div>
      <Handle className="node-handle output" position={Position.Right} type="source" />
    </div>
  );
}
