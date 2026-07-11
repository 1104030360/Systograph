import { Handle, Position, type NodeProps } from "reactflow";
import {
  AlertTriangle,
  Anchor,
  CheckCircle2,
  CircleDashed,
  CircleDotDashed,
  CircleHelp,
  CircleOff,
} from "lucide-react";
import type { FlowNodeData } from "../utils/graph";
import { compactId } from "../utils/format";
import { hasNodeLevelRisk, nodeStatusKey, nodeStatusLabel, type NodeStatusKey } from "../utils/assessment";

function StatusIcon({ status }: { status: NodeStatusKey }) {
  const Icon =
    status === "partial"
      ? CircleDotDashed
      : status === "undetermined"
        ? CircleHelp
        : status === "not_detected" || status === "not_applicable" || status === "not_configured"
          ? CircleOff
          : status === "needs_review" || status === "needs_confirmation"
            ? CircleDashed
            : status === "risk" || status === "missing" || status === "conflicted"
              ? AlertTriangle
              : CheckCircle2;

  return (
    <span className={`node-status s-${status}`} title={`Assessment: ${nodeStatusLabel(status)}`}>
      <Icon aria-hidden="true" size={13} />
      <span>{nodeStatusLabel(status)}</span>
    </span>
  );
}

export function SystemNode({ data }: NodeProps<FlowNodeData>) {
  const key = nodeStatusKey(data);
  const className = [
    "node",
    `s-${key}`,
    data.semantic_kind ? `k-${data.semantic_kind}` : "",
    hasNodeLevelRisk(data) ? "has-risk" : "",
    data.isSelected ? "is-selected" : "",
    data.isFocused && !data.isSelected ? "is-focused" : "",
    data.isDimmed ? "is-dimmed" : "",
    data.isProgressTarget ? "is-progress" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className} title={data.id} data-semantic-kind={data.semantic_kind}>
      <Handle className="node-handle" position={Position.Left} type="target" />
      <div className="node-top">
        <span className="node-slot">{data.subtitle ?? data.slot ?? data.type}</span>
        {data.semantic_kind === "profile_attachment" && data.primary_anchor_node_id ? (
          <span className="node-anchor" title={`Anchored to ${compactId(data.primary_anchor_node_id)}`}>
            <Anchor aria-hidden="true" size={11} />
          </span>
        ) : null}
        <StatusIcon status={key} />
      </div>
      <div className="node-title">{data.label}</div>
      {data.badges.length > 0 ? (
        <div className="node-badges">
          {data.badges.slice(0, data.activation ? 2 : 3).map((badge) => (
            <span className="node-badge" key={badge}>
              {badge}
            </span>
          ))}
          {data.activation ? (
            <span className={`node-activation a-${data.activation}`} title="Activation is independent from assessment status">
              {data.activation}
            </span>
          ) : null}
        </div>
      ) : data.activation ? (
        <div className="node-badges">
          <span className={`node-activation a-${data.activation}`} title="Activation is independent from assessment status">
            {data.activation}
          </span>
        </div>
      ) : null}
      <Handle className="node-handle" position={Position.Right} type="source" />
    </div>
  );
}
