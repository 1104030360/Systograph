# 這個檔案負責：依已投影的 nodes/edges 組出 GraphFiltersModel
# （status/type/flow/risk 篩選器 + lenses + highlight_and_dim 行為）。
# 不做 layout、不改 map；只從圖資料推導「點了會亮哪些 id」。
#
# 呼叫鏈：
#   GraphProjectionService.project()
#     → build_graph_filters(nodes, edges)
#         → 依 status / type / flow / risk 組 GraphFilterModel
#         → project_graph_lenses(...) 組 lenses
#     → GraphViewModel.filters
#   GraphProjectionService._edges()
#     → flow_id_from_edge_id(edge_id) 推導 flow_id
from __future__ import annotations

import re
from collections import defaultdict

from systograph.core.models.viewer import (
    GraphEdgeModel,
    GraphFilterModel,
    GraphFiltersModel,
    GraphNodeModel,
)
from systograph.core.services.graph_lens_projector import project_graph_lenses


# 做什麼：從 nodes/edges 建完整 GraphFiltersModel（available filters + lenses）
# 。
# 被誰呼叫：GraphProjectionService.project()。
# 自己呼叫：
#   1. 依 node.status / node.type 分組 → status/type filters
#   2. 依 edge.flow_id 分組 → flow filters（含相關 node/edge ids）
#   3. 有 risk_hint_ids 的 node/edge → "Has Risk Hint" filter
#   4. project_graph_lenses(nodes, edges) → lenses
# 行為固定：behavior="highlight_and_dim"（前端亮中的、暗其餘）。
def build_graph_filters(
    nodes: list[GraphNodeModel],
    edges: list[GraphEdgeModel],
) -> GraphFiltersModel:
    filters: list[GraphFilterModel] = []
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for node in nodes:
        if node.status:
            groups[("status", node.status)].append(node.id)
        if node.type:
            groups[("type", node.type)].append(node.id)
    filters.extend(
        GraphFilterModel(
            id=f"filter:{kind}:{value if kind == 'status' else _slug(value)}",
            label=f"{_humanize(kind)}: {_humanize(value)}",
            kind=kind,
            matches_node_ids=sorted(node_ids),
        )
        for (kind, value), node_ids in sorted(groups.items())
    )
    edge_ids_by_flow: dict[str, list[str]] = defaultdict(list)
    node_ids_by_edge = {edge.id: {edge.from_id, edge.to} for edge in edges}
    for edge in edges:
        if edge.flow_id is not None:
            edge_ids_by_flow[edge.flow_id].append(edge.id)
    for flow_id, edge_ids in edge_ids_by_flow.items():
        sorted_edge_ids = sorted(edge_ids)
        filters.append(
            GraphFilterModel(
                id=f"filter:flow:{flow_id.removeprefix('flow:')}",
                label=_humanize(flow_id.removeprefix("flow:")),
                kind="flow",
                matches_node_ids=sorted(
                    {
                        node_id
                        for edge_id in sorted_edge_ids
                        for node_id in node_ids_by_edge[edge_id]
                    }
                ),
                matches_edge_ids=sorted_edge_ids,
            )
        )
    risk_nodes = sorted(node.id for node in nodes if node.risk_hint_ids)
    risk_edges = sorted(edge.id for edge in edges if edge.risk_hint_ids)
    if risk_nodes or risk_edges:
        filters.append(
            GraphFilterModel(
                id="filter:risk:has_risk",
                label="Has Risk Hint",
                kind="risk",
                matches_node_ids=risk_nodes,
                matches_edge_ids=risk_edges,
            )
        )
    return GraphFiltersModel(
        available=filters,
        lenses=project_graph_lenses(nodes, edges),
        behavior="highlight_and_dim",
    )


# 做什麼：從 canonical edge_id（edge:<flow>:<rest>）推導 flow_id（flow:<flow>）
# 。
# 被誰呼叫：GraphProjectionService._edges() 填 GraphEdgeModel.flow_id。
# 自己呼叫：字串 split；格式不符回 None。
def flow_id_from_edge_id(edge_id: str) -> str | None:
    parts = edge_id.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "edge":
        return None
    return f"flow:{parts[1]}"


# 做什麼：把 snake/kebab 轉成 Title Case 顯示文字。
# 被誰呼叫：build_graph_filters（filter label）。
# 自己呼叫：re.sub。
def _humanize(value: str) -> str:
    return re.sub(r"[_:-]+", " ", value).title()


# 做什麼：把任意字串壓成穩定 slug（給 filter id 用）。
# 被誰呼叫：build_graph_filters（type filter id）。
# 自己呼叫：re.sub。
def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
