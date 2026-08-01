# 這個檔案負責：從已投影的 nodes/edges 算出六個固定 lens
# （data / control / evidence / governance / source / risk）的 membership。
# 不做 layout、不改 map；只回傳 GraphLensModel（哪些 node/edge 屬於該視角）。
#
# 呼叫鏈：
#   GraphProjectionService.project()
#     → build_graph_filters(nodes, edges)
#         → project_graph_lenses(nodes, edges)
#             → _build_lens × 6
#     → GraphFiltersModel.lenses → 前端 lens UI
from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from systograph.core.models.viewer import (
    GraphEdgeModel,
    GraphLensModel,
    GraphNodeModel,
)

NodePredicate = Callable[[GraphNodeModel], bool]
LensId = Literal[
    "lens:data",
    "lens:control",
    "lens:evidence",
    "lens:governance",
    "lens:source",
    "lens:risk",
]


# 做什麼：產出固定 6 個 GraphLensModel（順序固定）。
# 被誰呼叫：build_graph_filters()。
# 自己呼叫：對每個 lens 用 predicate 篩 node，再 _build_lens 補 edge
# membership。
# Lens 規則摘要：
#   data       → plane 在 ingestion/retrieval/memory
#   control    → plane=control 或特定 agent/tool reference
#   evidence   → plane=evidence 或 node 有 evidence_ids
#   governance → plane=governance_observability 或 output_guardrail
#   source     → _is_source_node（loader/corpus/source/connector）
#   risk       → node 有 risk_hint_ids 或 conflict_fields
def project_graph_lenses(
    nodes: list[GraphNodeModel],
    edges: list[GraphEdgeModel],
) -> list[GraphLensModel]:
    predicates: list[tuple[LensId, str, NodePredicate]] = [
        (
            "lens:data",
            "Data",
            lambda node: (
                node.plane_id
                in {"ingestion_indexing", "retrieval", "memory_state"}
            ),
        ),
        (
            "lens:control",
            "Control",
            lambda node: (
                node.plane_id == "control"
                or node.reference_node_id
                in {"tool_using_generator", "agent_runtime", "tool_network"}
            ),
        ),
        (
            "lens:evidence",
            "Evidence",
            lambda node: (
                node.plane_id == "evidence" or bool(node.evidence_ids)
            ),
        ),
        (
            "lens:governance",
            "Governance",
            lambda node: (
                node.plane_id == "governance_observability"
                or node.reference_node_id == "output_guardrail"
            ),
        ),
        (
            "lens:source",
            "Source",
            _is_source_node,
        ),
        (
            "lens:risk",
            "Risk",
            lambda node: bool(node.risk_hint_ids or node.conflict_fields),
        ),
    ]
    return [
        _build_lens(lens_id, label, predicate, nodes, edges)
        for lens_id, label, predicate in predicates
    ]


# 做什麼：用 predicate 選中的 nodes，再推導相關 edges，組出一個
# GraphLensModel。
# 被誰呼叫：project_graph_lenses()。
# 自己呼叫：predicate(node)；_edge_has_signal（僅 evidence/risk lens）。
# Edge 規則：端點在 lens 內的邊；evidence/risk 另可因 edge 自身 signal 入選。
# supported=False 時帶 unavailable_reason（目前圖沒有該 lens 的成員）。
def _build_lens(
    lens_id: LensId,
    label: str,
    predicate: NodePredicate,
    nodes: list[GraphNodeModel],
    edges: list[GraphEdgeModel],
) -> GraphLensModel:
    node_ids = {node.id for node in nodes if predicate(node)}
    edge_ids = {
        edge.id
        for edge in edges
        if edge.from_id in node_ids
        or edge.to in node_ids
        or (
            lens_id in {"lens:evidence", "lens:risk"}
            and _edge_has_signal(edge, lens_id)
        )
    }
    supported = bool(node_ids or edge_ids)
    return GraphLensModel(
        id=lens_id,
        label=label,
        supported=supported,
        unavailable_reason=(
            None
            if supported
            else "The current projection has no backend-provided membership."
        ),
        matches_node_ids=sorted(node_ids),
        matches_edge_ids=sorted(edge_ids),
    )


# 做什麼：判斷節點是否屬 Source lens（文件載入 / corpus / connector 等）。
# 被誰呼叫：project_graph_lenses 的 Source predicate。
# 自己呼叫：看 reference_node_id 或 type 字串是否含 loader/corpus/source/
# connector。
def _is_source_node(node: GraphNodeModel) -> bool:
    if node.reference_node_id in {"document_loader", "metadata_extractor"}:
        return True
    canonical_type = node.type or ""
    return any(
        marker in canonical_type
        for marker in ("loader", "corpus", "source", "connector")
    )


# 做什麼：判斷邊本身是否帶有該 lens 的 signal（不靠端點）。
# 被誰呼叫：_build_lens（僅 lens:evidence / lens:risk）。
# 自己呼叫：risk → edge.risk_hint_ids；evidence → edge.evidence_ids。
def _edge_has_signal(edge: GraphEdgeModel, lens_id: LensId) -> bool:
    if lens_id == "lens:risk":
        return bool(edge.risk_hint_ids)
    return bool(edge.evidence_ids)
