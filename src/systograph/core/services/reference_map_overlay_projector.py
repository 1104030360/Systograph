# 這個檔案負責：協調 reference capability + profile attachment 兩層 overlay，
# 合成一份 ReferenceOverlayProjection 給 GraphProjectionService 合併進
# GraphViewModel。
# 本身不做 assessment / profile 推論；只組裝 builders 輸出與 details lookup。
#
# 呼叫鏈：
#   GraphProjectionService.project()
#     → ReferenceMapOverlayProjector.project(index, profile_result,
# node_ids_by_source)
#         → ReferenceOverlayContext(...)
#         → build_reference_capability_overlay(catalog, context)
#         → build_profile_attachment_overlay(context)
#         → ReferenceOverlayProjection（nodes / relationships / filters /
# details dicts）
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from systograph.core.models.profile_signal import (
    MappingCompleteness,
    ProfileInferenceResult,
)
from systograph.core.models.viewer import (
    GraphFilterModel,
    GraphNodeModel,
    GraphRelationshipModel,
)
from systograph.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from systograph.core.services.profile_attachment_overlay_builder import (
    build_profile_attachment_overlay,
)
from systograph.core.services.reference_capability_overlay_builder import (
    build_reference_capability_overlay,
)
from systograph.core.services.reference_overlay_context import (
    ReferenceOverlayContext,
)
from systograph.core.services.system_map_index import SystemMapIndex


# 做什麼：一次 overlay 投影的完整輸出（節點、關係、篩選、側欄 lookup）。
# 被誰用：GraphProjectionService.project() 讀取後併入 GraphViewModel。
# 內含：
#   - nodes / relationships / filters → 畫布與篩選 UI
#   - mapping_completeness → 可選的完整度分數
#   - *_by_id → details 側欄用的 JSON dict（唯讀 MappingProxyType）
# 自己呼叫：無方法；純資料承載。
@dataclass(frozen=True, slots=True)
class ReferenceOverlayProjection:
    nodes: tuple[GraphNodeModel, ...] = ()
    relationships: tuple[GraphRelationshipModel, ...] = ()
    filters: tuple[GraphFilterModel, ...] = ()
    mapping_completeness: MappingCompleteness | None = None
    reference_assessments_by_id: Mapping[str, dict[str, Any]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    profile_findings_by_id: Mapping[str, dict[str, Any]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    capability_candidates_by_id: Mapping[str, dict[str, Any]] = field(
        default_factory=lambda: MappingProxyType({})
    )


# 做什麼：overlay 投影協調者；載入 catalog，串起兩個 builder，打包結果。
# 被誰用：GraphProjectionService（預設注入）；unit tests。
# 自己呼叫：CapabilityReferenceMapLoader、兩個 build_*_overlay、
# ReferenceOverlayContext。
class ReferenceMapOverlayProjector:
    # 做什麼：建構時載入固定 capability reference catalog（10 planes / 52
    # nodes）。
    # 被誰呼叫：GraphProjectionService.__init__ 或測試 new Projector()。
    # 自己呼叫：CapabilityReferenceMapLoader().load()。
    def __init__(self) -> None:
        self._catalog = CapabilityReferenceMapLoader().load()

    # 做什麼：入口；組 context → 跑兩層 overlay → 合併成
    # ReferenceOverlayProjection。
    # 被誰呼叫：GraphProjectionService.project()。
    # 自己呼叫：
    #   1. ReferenceOverlayContext（index + profile + node_ids_by_source）
    #   2. build_reference_capability_overlay → reference nodes/relationships
    #   3. build_profile_attachment_overlay → profile/candidate nodes + filters
    #   4. 把 assessments / profiles / candidates dump 成 details lookup dict
    # 注意：profile_result 可為 None（仍會畫 undetermined reference nodes）。
    def project(
        self,
        index: SystemMapIndex,
        *,
        profile_result: ProfileInferenceResult | None,
        node_ids_by_source: Mapping[str, str],
    ) -> ReferenceOverlayProjection:
        context = ReferenceOverlayContext(
            index=index,
            profile_result=profile_result,
            node_ids_by_source=MappingProxyType(dict(node_ids_by_source)),
        )
        reference_nodes, reference_relationships = (
            build_reference_capability_overlay(self._catalog, context)
        )
        profile_nodes, profile_relationships, filters = (
            build_profile_attachment_overlay(context)
        )
        assessments = (
            profile_result.reference_capability_assessments
            if profile_result is not None
            else ()
        )
        profiles = (
            profile_result.profiles if profile_result is not None else ()
        )
        candidates = (
            profile_result.capability_candidate_components
            if profile_result is not None
            else ()
        )
        return ReferenceOverlayProjection(
            nodes=(*reference_nodes, *profile_nodes),
            relationships=(
                *reference_relationships,
                *profile_relationships,
            ),
            filters=filters,
            mapping_completeness=(
                profile_result.mapping_completeness
                if profile_result is not None
                else None
            ),
            reference_assessments_by_id=MappingProxyType(
                {
                    item.reference_node_id: item.model_dump(mode="json")
                    for item in assessments
                }
            ),
            profile_findings_by_id=MappingProxyType(
                {
                    item.profile_id: item.model_dump(mode="json")
                    for item in profiles
                }
            ),
            capability_candidates_by_id=MappingProxyType(
                {item.id: item.model_dump(mode="json") for item in candidates}
            ),
        )
