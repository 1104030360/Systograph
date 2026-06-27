import { Handle, Position, type NodeProps } from "reactflow";
import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
import type { FlowNodeData } from "../utils/graph";

type NodeStatusKey =
  | "needs_confirmation"
  | "not_applicable"
  | "not_configured"
  | "missing"
  | "confirmed"
  | "detected";

const MISSING_REQUIRED_SLOT_RISK_PREFIX = "risk:missing_required_slot:";

function nodeLevelRiskCount(data: Pick<FlowNodeData, "risk_hint_ids">) {
  return data.risk_hint_ids.filter((riskId) => !riskId.startsWith(MISSING_REQUIRED_SLOT_RISK_PREFIX)).length;
}

/**
 * Visual status key.
 *
 * Missing-slot hints describe the map's overall completeness, not a detected
 * node defect. Keep them available in details, but do not let them override the
 * node's own status color.
 */
function statusKey(data: Pick<FlowNodeData, "status">): NodeStatusKey {
  if (data.status === "needs_confirmation") return "needs_confirmation";
  if (data.status === "not_applicable") return "not_applicable";
  if (data.status === "not_configured") return "not_configured";
  if (data.status === "missing") return "missing";
  if (data.status === "confirmed") return "confirmed";
  return "detected";
}

function StatusIcon({ statusKey: key, hasRisk }: { statusKey: NodeStatusKey; hasRisk: boolean }) {
  if (hasRisk) return <AlertTriangle size={15} style={{ color: "var(--risk)" }} />;
  if (key === "missing") return <AlertTriangle size={15} style={{ color: "var(--risk)" }} />;
  if (key === "needs_confirmation") return <CircleDashed size={15} style={{ color: "var(--unmapped)" }} />;
  if (key === "confirmed") return <CheckCircle2 size={15} style={{ color: "var(--accent-strong)" }} />;
  return null;
}

export function SystemNode({ data }: NodeProps<FlowNodeData>) {
  const key = statusKey(data);
  const riskCount = nodeLevelRiskCount(data);
  const hasRisk = riskCount > 0;
  const className = [
    "node",
    `s-${key}`,
    hasRisk ? "has-risk" : "",
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
        <span
          className={hasRisk ? "node-status-ico has-risk" : "node-status-ico"}
          aria-label={hasRisk ? `${riskCount} risk hint${riskCount === 1 ? "" : "s"}` : undefined}
          title={hasRisk ? "Review risk hints" : undefined}
        >
          <StatusIcon statusKey={key} hasRisk={hasRisk} />
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
