import { Handle, Position, type NodeProps } from "reactflow";
import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
import type { FlowNodeData } from "../utils/graph";

type NodeStatusKey =
  | "risk"
  | "needs_confirmation"
  | "not_configured"
  | "missing"
  | "confirmed"
  | "detected";

/** Visual status key — risk always wins so attention is never hidden. */
function statusKey(data: Pick<FlowNodeData, "risk_hint_ids" | "status">): NodeStatusKey {
  if (data.risk_hint_ids.length > 0) return "risk";
  if (data.status === "needs_confirmation") return "needs_confirmation";
  if (data.status === "not_configured") return "not_configured";
  if (data.status === "missing") return "missing";
  if (data.status === "confirmed") return "confirmed";
  return "detected";
}

function StatusIcon({ statusKey: key }: { statusKey: NodeStatusKey }) {
  if (key === "risk") return <AlertTriangle size={15} style={{ color: "var(--risk)" }} />;
  if (key === "needs_confirmation") return <CircleDashed size={15} style={{ color: "var(--unmapped)" }} />;
  if (key === "confirmed") return <CheckCircle2 size={15} style={{ color: "var(--accent-strong)" }} />;
  return null;
}

export function SystemNode({ data }: NodeProps<FlowNodeData>) {
  const key = statusKey(data);
  const className = [
    "node",
    `s-${key}`,
    data.isSelected ? "is-selected" : "",
    data.isFocused && !data.isSelected ? "is-focused" : "",
    data.isDimmed ? "is-dimmed" : "",
    data.isProgressTarget ? "is-progress" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className} title={data.id}>
      <Handle className="node-handle" position={Position.Left} type="target" />
      <div className="node-top">
        <span className="node-slot">{data.subtitle ?? data.slot ?? data.type}</span>
        <span className="node-status-ico">
          <StatusIcon statusKey={key} />
        </span>
      </div>
      <div className="node-title">{data.label}</div>
      {data.badges.length > 0 ? (
        <div className="node-badges">
          {data.badges.slice(0, 3).map((badge) => (
            <span className="node-badge" key={badge}>
              {badge}
            </span>
          ))}
        </div>
      ) : null}
      <Handle className="node-handle" position={Position.Right} type="source" />
    </div>
  );
}
