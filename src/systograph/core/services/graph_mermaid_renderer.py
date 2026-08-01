from __future__ import annotations

import json
import re
from collections import defaultdict

from systograph.core.models.viewer import GraphNodeModel, GraphViewModel


class GraphMermaidRenderer:
    def render(self, graph: GraphViewModel) -> str:
        aliases = {
            node.id: f"N{position:03d}"
            for position, node in enumerate(graph.nodes)
        }
        groups: dict[str, list[GraphNodeModel]] = defaultdict(list)
        for node in graph.nodes:
            groups[node.plane_id or "semantic_overlay"].append(node)
        lines = [
            "flowchart LR",
            "%% "
            f"build={graph.build_id or 'unscoped'} "
            f"scan={graph.scan_id or 'unscoped'} "
            f"environment={graph.environment_id or 'unscoped'} "
            "artifact_set="
            f"{graph.artifact_set_version or 'unscoped'}",
        ]
        for group_id, nodes in groups.items():
            lines.append(
                "  subgraph "
                f"{_safe_id(group_id)}[{json.dumps(_label(group_id))}]"
            )
            for node in nodes:
                label = "\\n".join(
                    (
                        node.label,
                        node.semantic_kind or "graph_node",
                        node.id,
                    )
                )
                lines.append(f"    {aliases[node.id]}[{json.dumps(label)}]")
            lines.append("  end")
        for edge in graph.edges:
            edge_label = " / ".join(
                value
                for value in (edge.relationship, edge.id)
                if value is not None
            )
            lines.append(
                f"  {aliases[edge.from_id]} -->|{_label(edge_label)}| "
                f"{aliases[edge.to]}"
            )
        for relation in graph.relationships:
            lines.append(
                "  %% semantic relation "
                f"{relation.id}: {relation.source_node_id} "
                f"{relation.kind} {relation.target_node_id}"
            )
        return "\n".join(lines) + "\n"


def _safe_id(value: str) -> str:
    return "G_" + re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")


def _label(value: str) -> str:
    return re.sub(r"[|\[\]{}]", " ", value).replace('"', "'")
