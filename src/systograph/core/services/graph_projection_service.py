# 這個檔案負責：把 canonical AiSystemMapV2 投影成前端用的 GraphViewModel。
# 只做「語意圖投影」，不改 map、不算 layout（座標由前端 ELK 處理）。
#
# 呼叫鏈：
#   ViewerSessionService.build / load_map / project_to_graph
#     → GraphProjectionService.project(AiSystemMapV2, profile_result?)
#         → SystemMapIndex.from_map
#         → _nodes / _edges（repo_component + unmapped + topology edges）
#         → ReferenceMapOverlayProjector.project（reference / profile overlay）
#         → build_graph_filters（lenses + filters）
#     → GraphViewModel → ViewerLoadResult / Markdown / Mermaid renderer
from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from typing import Any

from systograph.core.models.ai_system_map_v2 import (
    REFERENCE_MAP_VERSION,
    AiSystemMapV2,
)
from systograph.core.models.profile_signal import ProfileInferenceResult
from systograph.core.models.viewer import (
    GraphDetailsModel,
    GraphEdgeModel,
    GraphEndpointModel,
    GraphNodeModel,
    GraphRecommendedNextCheckModel,
    GraphViewModel,
)
from systograph.core.services.graph_projection_filters import (
    build_graph_filters,
    flow_id_from_edge_id,
)
from systograph.core.services.path_safety_service import (
    is_project_relative_posix_path,
)
from systograph.core.services.reference_map_overlay_projector import (
    ReferenceMapOverlayProjector,
)
from systograph.core.services.system_map_index import SystemMapIndex

GRAPH_SCHEMA_VERSION = "graph-view-model/v1"
# Node id encoding (compatible under same schema string):
#   node:{kind}:{slug}~{sha256(canonical_id)[:8]}
# Slug alone is not injective; hash makes graph ids 1:1 with source ids.


# 做什麼：canonical map → GraphViewModel 的投影服務（base graph + overlay）。
# 被誰用：ViewerSessionService（主要）；graph renderer / unit tests。
# 自己呼叫：SystemMapIndex、_nodes/_edges、ReferenceMapOverlayProjector、
#           build_graph_filters。
class GraphProjectionService:
    # 做什麼：注入（或預設建立）overlay projector。
    # 被誰呼叫：ViewerSessionService.__init__ 或測試注入 fake。
    # 自己呼叫：預設 ReferenceMapOverlayProjector()。
    def __init__(
        self,
        overlay_projector: ReferenceMapOverlayProjector | None = None,
    ) -> None:
        self._overlay_projector = (
            overlay_projector or ReferenceMapOverlayProjector()
        )

    # 做什麼：入口；組出完整 GraphViewModel
    #         （nodes/edges/relationships/details/filters）。
    # 被誰呼叫：ViewerSessionService.build / load_map / project_to_graph。
    # 自己呼叫：
    #   1. 檢查 artifact_ref 必須是專案相對路徑
    #   2. SystemMapIndex.from_map
    #   3. _nodes → base 節點；_edges → topology 邊
    #   4. overlay_projector.project（reference + profile 疊加）
    #   5. 節點順序：reference → base → 其他 overlay
    #   6. build_graph_filters + overlay.filters
    #   7. 組 GraphDetailsModel / GraphViewModel
    def project(
        self,
        system_map: AiSystemMapV2,
        *,
        profile_result: ProfileInferenceResult | None = None,
        artifact_ref: str | None = None,
        recommended_next_checks: (
            Sequence[GraphRecommendedNextCheckModel] | None
        ) = None,
    ) -> GraphViewModel:
        if artifact_ref is not None and not is_project_relative_posix_path(
            artifact_ref
        ):
            raise ValueError("artifact_ref must be build-relative")
        index = SystemMapIndex.from_map(system_map)
        base_nodes = self._nodes(system_map, index)
        node_ids_by_source = {
            node.source_id: node.id for node in base_nodes if node.source_id
        }
        edges = self._edges(system_map, index, node_ids_by_source)
        overlay = self._overlay_projector.project(
            index,
            profile_result=profile_result,
            node_ids_by_source=node_ids_by_source,
        )
        reference_nodes = [
            node
            for node in overlay.nodes
            if node.semantic_kind == "reference_capability"
        ]
        semantic_overlay_nodes = [
            node
            for node in overlay.nodes
            if node.semantic_kind != "reference_capability"
        ]
        nodes = [*reference_nodes, *base_nodes, *semantic_overlay_nodes]
        _assert_unique_graph_node_ids(nodes)
        filters = build_graph_filters(nodes, edges)
        filters = filters.model_copy(
            update={"available": [*filters.available, *overlay.filters]}
        )
        return GraphViewModel(
            schema_version=GRAPH_SCHEMA_VERSION,
            source_schema_version=system_map.source_schema_version
            or system_map.schema_version,
            project_id=system_map.project.project_id,
            scan_id=system_map.scan_id,
            build_id=system_map.build_id,
            environment_id=system_map.environment_id,
            artifact_set_version=system_map.artifact_set_version,
            generated_from_build_id=system_map.generated_from_build_id,
            reference_map_version=REFERENCE_MAP_VERSION,
            mapping_completeness=overlay.mapping_completeness,
            map_json=artifact_ref,
            summary={
                "project_name": system_map.project.name,
                "schema_version": system_map.schema_version,
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
            nodes=nodes,
            edges=edges,
            relationships=list(overlay.relationships),
            endpoints=_endpoints_for_graph(system_map, index),
            recommended_next_checks=list(recommended_next_checks or ()),
            details=GraphDetailsModel(
                evidence_by_id={
                    evidence.evidence_id: evidence.model_dump(mode="json")
                    for evidence in system_map.evidence
                },
                risk_hints_by_id={
                    risk.risk_id: _risk_detail(risk.model_dump(mode="json"))
                    for risk in system_map.risk_hints
                },
                reference_assessments_by_id=dict(
                    overlay.reference_assessments_by_id
                ),
                profile_findings_by_id=dict(overlay.profile_findings_by_id),
                capability_candidates_by_id=dict(
                    overlay.capability_candidates_by_id
                ),
            ),
            filters=filters,
        )

    # 做什麼：從 canonical components + unmapped 組 base GraphNodeModel。
    # 被誰呼叫：project()。
    # 自己呼叫：index.component_by_id / unmapped_by_id；
    #           _component_node_id / _unmapped_node_id /
    #           _humanize / _risk_ids_for_fact。
    def _nodes(
        self,
        system_map: AiSystemMapV2,
        index: SystemMapIndex,
    ) -> list[GraphNodeModel]:
        nodes: list[GraphNodeModel] = []
        for component_ref in system_map.components:
            component = index.component_by_id(component_ref.component_id)
            if component is None:
                continue
            evidence_ids = list(component.evidence_ids)
            legacy_slot = component.metadata.get("legacy_slot")
            slot = legacy_slot if isinstance(legacy_slot, str) else None
            nodes.append(
                GraphNodeModel(
                    id=_component_node_id(component.component_id, slot),
                    source_id=component.component_id,
                    component_id=component.component_id,
                    plane_id=component.layer,
                    type=component.canonical_type,
                    semantic_kind="repo_component",
                    slot=slot,
                    status=component.status,
                    activation=component.activation,
                    label=component.display_name,
                    subtitle=_humanize(component.layer),
                    badges=[
                        component.status,
                        component.activation,
                        component.canonical_type,
                    ],
                    evidence_ids=evidence_ids,
                    risk_hint_ids=_risk_ids_for_fact(
                        system_map,
                        index,
                        target_ids={component.component_id},
                        evidence_ids=set(evidence_ids),
                    ),
                )
            )
        for unmapped_ref in system_map.unmapped_components:
            unmapped = index.unmapped_by_id(unmapped_ref.unmapped_id)
            if unmapped is None:
                continue
            evidence_ids = list(unmapped.evidence_ids)
            nodes.append(
                GraphNodeModel(
                    id=_unmapped_node_id(unmapped.unmapped_id),
                    source_id=unmapped.unmapped_id,
                    type=unmapped.observed_kind,
                    semantic_kind="unmapped_component",
                    status=unmapped.status,
                    activation="unknown",
                    label=_humanize(unmapped.observed_kind),
                    subtitle=unmapped.reason,
                    badges=[unmapped.status, "unmapped"],
                    evidence_ids=evidence_ids,
                    risk_hint_ids=_risk_ids_for_fact(
                        system_map,
                        index,
                        target_ids={unmapped.unmapped_id},
                        evidence_ids=set(evidence_ids),
                    ),
                )
            )
        return nodes

    # 做什麼：把 canonical edges 轉成 GraphEdgeModel
    #         （source/target 改成 graph node id）。
    # 被誰呼叫：project()。
    # 自己呼叫：index.edge_by_id；flow_id_from_edge_id；
    #           _humanize；_risk_ids_for_fact。
    # 注意：只用 topology edges，不會用 overlay relationships 冒充拓樸邊。
    def _edges(
        self,
        system_map: AiSystemMapV2,
        index: SystemMapIndex,
        node_ids_by_source: dict[str, str],
    ) -> list[GraphEdgeModel]:
        edges: list[GraphEdgeModel] = []
        for edge_ref in system_map.edges:
            edge = index.edge_by_id(edge_ref.edge_id)
            if edge is None:
                continue
            edges.append(
                GraphEdgeModel(
                    id=f"graph:{edge.edge_id}",
                    source_id=edge.edge_id,
                    flow_id=flow_id_from_edge_id(edge.edge_id),
                    from_id=node_ids_by_source[edge.source],
                    to=node_ids_by_source[edge.target],
                    relationship=edge.relationship,
                    label=_humanize(edge.relationship),
                    evidence_ids=list(edge.evidence_ids),
                    risk_hint_ids=_risk_ids_for_fact(
                        system_map,
                        index,
                        target_ids={edge.source, edge.target},
                        evidence_ids=set(edge.evidence_ids),
                    ),
                )
            )
        return edges


# 做什麼：依 component_id 型別產生穩定且可逆對應的 graph node id。
# 被誰呼叫：_nodes()；測試對照 expected id。
# 自己呼叫：_stable_graph_token()。
# 注意：不可只靠 _slug()——不同 canonical id 可能塌成同一 slug。
def _component_node_id(component_id: str, legacy_slot: str | None) -> str:
    if component_id.startswith("component:slot_placeholder:"):
        token = _stable_graph_token(
            component_id,
            slug_source=legacy_slot or component_id,
        )
        return f"node:slot:{token}"
    if component_id.startswith("extension:"):
        return f"node:extension:{_stable_graph_token(component_id)}"
    return f"node:component:{_stable_graph_token(component_id)}"


# 做什麼：為 unmapped fact 產生穩定且不撞 id 的 graph node id。
# 被誰呼叫：_nodes()；測試對照 expected id。
# 自己呼叫：_stable_graph_token()。
def _unmapped_node_id(unmapped_id: str) -> str:
    return f"node:unmapped:{_stable_graph_token(unmapped_id)}"


# 做什麼：投影結束前強制 graph node id 唯一；撞 id 直接 fail loud。
# 被誰呼叫：project()。
# 注意：含 reference / profile overlay 節點，不只 base graph。
def _assert_unique_graph_node_ids(nodes: Sequence[GraphNodeModel]) -> None:
    seen: dict[str, str] = {}
    for node in nodes:
        previous = seen.get(node.id)
        if previous is not None:
            raise ValueError(
                "duplicate graph node id "
                f"{node.id!r}: {previous!r} and "
                f"{node.source_id or node.id!r}"
            )
        seen[node.id] = node.source_id or node.id


# 做什麼：把 canonical endpoints 投影成 GraphEndpointModel（含 legacy slot）。
# 被誰呼叫：project()。
# 自己呼叫：index.component_by_id 取 metadata.legacy_slot。
def _endpoints_for_graph(
    system_map: AiSystemMapV2,
    index: SystemMapIndex,
) -> list[GraphEndpointModel]:
    endpoints: list[GraphEndpointModel] = []
    for endpoint in system_map.endpoints:
        slot: str | None = None
        if endpoint.component_id is not None:
            component = index.component_by_id(endpoint.component_id)
            if component is not None:
                legacy_slot = component.metadata.get("legacy_slot")
                slot = legacy_slot if isinstance(legacy_slot, str) else None
        endpoints.append(
            GraphEndpointModel(
                endpoint_id=endpoint.endpoint_id,
                value=endpoint.value,
                endpoint_type=endpoint.endpoint_type,
                method=endpoint.method,
                component_id=endpoint.component_id,
                slot=slot,
            )
        )
    return endpoints


# 做什麼：找出跟某個 fact 相關的 risk_hint id
#         （component / evidence / endpoint；file 見下方契約）。
# 被誰呼叫：_nodes()、_edges()。
# 自己呼叫：掃 system_map.risk_hints；
#           endpoint risk 經 index.endpoint_by_id → component_id。
# 注意：
#   - base graph 沒有 endpoint / file node。
#   - endpoint-targeted risk 必須 join 回 component。
#   - file-targeted risk 不另外做 path→component 啟發式 join；
#     只在 risk.evidence_id 已掛在該 node/edge 的 evidence_ids 時
#     （本函式第一個分支）進入 membership。orphan file risk 仍留在
#     details.risk_hints_by_id，供 markdown Network/scan quality 顯示。
def _risk_ids_for_fact(
    system_map: AiSystemMapV2,
    index: SystemMapIndex,
    *,
    target_ids: set[str],
    evidence_ids: set[str],
) -> list[str]:
    matched: list[str] = []
    for risk in system_map.risk_hints:
        if risk.evidence_id in evidence_ids:
            matched.append(risk.risk_id)
            continue
        if risk.target_type == "evidence" and risk.target in evidence_ids:
            matched.append(risk.risk_id)
            continue
        if risk.target_type == "component" and risk.target in target_ids:
            matched.append(risk.risk_id)
            continue
        if risk.target_type == "endpoint":
            endpoint = index.endpoint_by_id(risk.target)
            if (
                endpoint is not None
                and endpoint.component_id is not None
                and endpoint.component_id in target_ids
            ):
                matched.append(risk.risk_id)
    return sorted(matched)


# 做什麼：把 risk dict 補上前端好讀的 title / severity / description。
# 被誰呼叫：project() 組 details.risk_hints_by_id 時。
# 自己呼叫：_humanize(type)。
def _risk_detail(detail: dict[str, Any]) -> dict[str, Any]:
    detail["title"] = _humanize(str(detail["type"]))
    detail["severity"] = detail.get("severity_hint") or "review"
    detail["description"] = detail["rationale"]
    return detail


# 做什麼：把 snake/kebab id 轉成 Title Case 顯示文字。
# 被誰呼叫：_nodes / _edges / _risk_detail。
# 自己呼叫：re.sub。
def _humanize(value: str) -> str:
    return re.sub(r"[_:-]+", " ", value).title()


# 做什麼：把任意字串壓成穩定 slug（給 node id 的可讀前綴）。
# 被誰呼叫：_stable_graph_token()。
# 自己呼叫：re.sub。
# 注意：slug 本身不是 injective；必須搭配 hash 才可當 graph id。
def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()


# 做什麼：產生 `slug~hash8` token，hash 取自完整 canonical id 的 sha256。
# 被誰呼叫：_component_node_id、_unmapped_node_id。
# 自己呼叫：_slug()；hashlib.sha256。
# 注意：slug_source 只影響可讀前綴（slot 可用 legacy_slot）；
#       唯一性一律靠 canonical_id 的 hash。
def _stable_graph_token(
    canonical_id: str,
    *,
    slug_source: str | None = None,
) -> str:
    digest = hashlib.sha256(canonical_id.encode("utf-8")).hexdigest()[:8]
    return f"{_slug(slug_source or canonical_id)}~{digest}"
