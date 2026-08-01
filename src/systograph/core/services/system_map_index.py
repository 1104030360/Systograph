# 這個檔案負責：把已驗證的 AiSystemMapV2 建成唯讀「電話簿」（ID → 物件索引）。
# 只做 lookup（查得到 / 查不到）；不做 validate、投影、推論、不讀檔案系統。
#
# 呼叫鏈：
#   CanonicalMapLoader.load() → AiSystemMapV2
#     → SystemMapIndex.from_map(...)
#         → GraphProjectionService（畫圖）
#         → DetailScanService / DetailScanTargetResolver（找相關檔）
#         → MappingEvidencePacketBuilder / mapping_proposal_routes
#         → profile / capability overlay（驗 anchor 是否存在）
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalCandidateFact,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEndpoint,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
    CanonicalRiskHint,
    CanonicalUnmappedComponent,
)


# 做什麼：canonical map 的唯讀索引；建一次 dict，之後 O(1) 用 ID 查。
# 被誰用：GraphProjection、DetailScan、Mapping packet、overlay builders。
# 自己呼叫：from_map → __init__ 建索引；各 *_by_id / 篩選方法供外部查詢。
# 契約：查詢成功回 deep copy；缺 ID 回 None（不丟例外）。
@dataclass(frozen=True, slots=True)
class SystemMapIndex:
    _components: tuple[CanonicalComponent, ...] = field(
        init=False,
        repr=False,
    )
    _edges: tuple[CanonicalEdge, ...] = field(
        init=False,
        repr=False,
    )
    _components_by_id: Mapping[str, CanonicalComponent] = field(
        init=False,
        repr=False,
    )
    _edges_by_id: Mapping[str, CanonicalEdge] = field(
        init=False,
        repr=False,
    )
    _evidence_by_id: Mapping[str, CanonicalEvidence] = field(
        init=False,
        repr=False,
    )
    _endpoints_by_id: Mapping[str, CanonicalEndpoint] = field(
        init=False,
        repr=False,
    )
    _risks_by_id: Mapping[str, CanonicalRiskHint] = field(
        init=False,
        repr=False,
    )
    _unmapped_by_id: Mapping[str, CanonicalUnmappedComponent] = field(
        init=False,
        repr=False,
    )
    _candidate_facts_by_id: Mapping[str, CanonicalCandidateFact] = field(
        init=False,
        repr=False,
    )

    # 做什麼：deep copy map，再建 tuple（保序）與 MappingProxyType（by-id）。
    # 被誰呼叫：from_map()；或少數地方直接 SystemMapIndex(map)。
    # 自己呼叫：system_map.model_copy(deep=True)；object.__setattr__（因
    # frozen）。
    # 注意：不檢查重複 ID；重複時 dict 後面覆蓋前面（應先經 validator）。
    def __init__(self, system_map: AiSystemMapV2) -> None:
        copied = system_map.model_copy(deep=True)
        object.__setattr__(self, "_components", tuple(copied.components))
        object.__setattr__(self, "_edges", tuple(copied.edges))
        object.__setattr__(
            self,
            "_components_by_id",
            MappingProxyType(
                {item.component_id: item for item in copied.components}
            ),
        )
        object.__setattr__(
            self,
            "_edges_by_id",
            MappingProxyType({item.edge_id: item for item in copied.edges}),
        )
        object.__setattr__(
            self,
            "_evidence_by_id",
            MappingProxyType(
                {item.evidence_id: item for item in copied.evidence}
            ),
        )
        object.__setattr__(
            self,
            "_endpoints_by_id",
            MappingProxyType(
                {item.endpoint_id: item for item in copied.endpoints}
            ),
        )
        object.__setattr__(
            self,
            "_risks_by_id",
            MappingProxyType(
                {item.risk_id: item for item in copied.risk_hints}
            ),
        )
        object.__setattr__(
            self,
            "_unmapped_by_id",
            MappingProxyType(
                {item.unmapped_id: item for item in copied.unmapped_components}
            ),
        )
        object.__setattr__(
            self,
            "_candidate_facts_by_id",
            MappingProxyType(
                {
                    item.candidate_fact_id: item
                    for item in copied.candidate_facts
                }
            ),
        )

    # 做什麼：對外工廠入口；把 AiSystemMapV2 建成 SystemMapIndex。
    # 被誰呼叫：GraphProjectionService、DetailScanService、
    # mapping_proposal_routes、
    #           overlay builders、相關 unit tests。
    # 自己呼叫：cls(system_map) → __init__。
    @classmethod
    def from_map(cls, system_map: AiSystemMapV2) -> SystemMapIndex:
        return cls(system_map)

    # 做什麼：用 component_id 查單一元件；缺則 None。
    # 被誰呼叫：DetailScanTargetResolver、GraphProjection、overlay builders。
    # 自己呼叫：_components_by_id.get + model_copy(deep=True)。
    def component_by_id(self, component_id: str) -> CanonicalComponent | None:
        component = self._components_by_id.get(component_id)
        if component is None:
            return None
        return component.model_copy(deep=True)

    # 做什麼：用 edge_id 查單一邊；缺則 None。
    # 被誰呼叫：需要單筆 edge 的 consumer / tests。
    # 自己呼叫：_edges_by_id.get + deep copy。
    def edge_by_id(self, edge_id: str) -> CanonicalEdge | None:
        edge = self._edges_by_id.get(edge_id)
        return edge.model_copy(deep=True) if edge is not None else None

    # 做什麼：用 evidence_id 查單筆證據；缺則 None。
    # 被誰呼叫：需要單筆 evidence 的 consumer / tests。
    # 自己呼叫：_evidence_by_id.get + deep copy。
    def evidence_by_id(self, evidence_id: str) -> CanonicalEvidence | None:
        evidence = self._evidence_by_id.get(evidence_id)
        return evidence.model_copy(deep=True) if evidence is not None else None

    # 做什麼：用 endpoint_id 查單一 endpoint；缺則 None。
    # 被誰呼叫：需要單筆 endpoint 的 consumer / tests。
    # 自己呼叫：_endpoints_by_id.get + deep copy。
    def endpoint_by_id(self, endpoint_id: str) -> CanonicalEndpoint | None:
        endpoint = self._endpoints_by_id.get(endpoint_id)
        return endpoint.model_copy(deep=True) if endpoint is not None else None

    # 做什麼：用 risk_id 查單一風險提示；缺則 None。
    # 被誰呼叫：需要單筆 risk 的 consumer / tests。
    # 自己呼叫：_risks_by_id.get + deep copy。
    def risk_by_id(self, risk_id: str) -> CanonicalRiskHint | None:
        risk = self._risks_by_id.get(risk_id)
        return risk.model_copy(deep=True) if risk is not None else None

    # 做什麼：用 unmapped_id 查未映射元件；缺則 None。
    # 被誰呼叫：MappingEvidencePacketBuilder（找不到時由 builder 自己 raise）。
    # 自己呼叫：_unmapped_by_id.get + deep copy。
    def unmapped_by_id(
        self,
        unmapped_id: str,
    ) -> CanonicalUnmappedComponent | None:
        unmapped = self._unmapped_by_id.get(unmapped_id)
        return unmapped.model_copy(deep=True) if unmapped is not None else None

    # 做什麼：用 candidate_fact_id 查 candidate fact；缺則 None。
    # 被誰呼叫：需要 candidate 的 consumer / tests。
    # 自己呼叫：_candidate_facts_by_id.get + deep copy。
    def candidate_fact_by_id(
        self,
        candidate_fact_id: str,
    ) -> CanonicalCandidateFact | None:
        candidate = self._candidate_facts_by_id.get(candidate_fact_id)
        if candidate is None:
            return None
        return candidate.model_copy(deep=True)

    # 做什麼：依 canonical_type 篩選元件（保留 map 原始順序）。
    # 被誰呼叫：graph projection / filter 相關路徑。
    # 自己呼叫：掃 _components tuple + deep copy。
    def components_by_type(
        self,
        canonical_type: str,
    ) -> tuple[CanonicalComponent, ...]:
        return tuple(
            component.model_copy(deep=True)
            for component in self._components
            if component.canonical_type == canonical_type
        )

    # 做什麼：依 layer 篩選元件（保留 map 原始順序）。
    # 被誰呼叫：graph projection / filter 相關路徑。
    # 自己呼叫：掃 _components tuple + deep copy。
    def components_by_layer(
        self,
        layer: str,
    ) -> tuple[CanonicalComponent, ...]:
        return tuple(
            component.model_copy(deep=True)
            for component in self._components
            if component.layer == layer
        )

    # 做什麼：找出從某 component 指出去的邊（edge.source == component_id）。
    # 被誰呼叫：需要鄰居關係的 graph / projection 路徑。
    # 自己呼叫：掃 _edges tuple 過濾（目前無 O(1) 反向索引）。
    def outgoing_edges(
        self,
        component_id: str,
    ) -> tuple[CanonicalEdge, ...]:
        return tuple(
            edge.model_copy(deep=True)
            for edge in self._edges
            if edge.source == component_id
        )

    # 做什麼：找出指向某 component 的邊（edge.target == component_id）。
    # 被誰呼叫：需要鄰居關係的 graph / projection 路徑。
    # 自己呼叫：掃 _edges tuple 過濾。
    def incoming_edges(
        self,
        component_id: str,
    ) -> tuple[CanonicalEdge, ...]:
        return tuple(
            edge.model_copy(deep=True)
            for edge in self._edges
            if edge.target == component_id
        )

    # 做什麼：依請求順序批次取 evidence；未知 ID 跳過（不插 None）。
    # 被誰呼叫：MappingEvidencePacketBuilder；
    # related_locations_for_evidence_ids。
    # 自己呼叫：_evidence_by_id.get + deep copy。
    def evidence_for_ids(
        self,
        ids: Iterable[str],
    ) -> tuple[CanonicalEvidence, ...]:
        evidence: list[CanonicalEvidence] = []
        for evidence_id in ids:
            item = self._evidence_by_id.get(evidence_id)
            if item is not None:
                evidence.append(item.model_copy(deep=True))
        return tuple(evidence)

    # 做什麼：從 evidence ids 抽出 location，並依 (path, lines, pointer, key)
    # 去重。
    # 被誰呼叫：DetailScanTargetResolver（找相關檔案路徑）。
    # 自己呼叫：evidence_for_ids()，再對 location 去重 + deep copy。
    def related_locations_for_evidence_ids(
        self,
        ids: Iterable[str],
    ) -> tuple[CanonicalEvidenceLocation, ...]:
        locations: list[CanonicalEvidenceLocation] = []
        seen: set[tuple[str | int | None, ...]] = set()
        for evidence in self.evidence_for_ids(ids):
            location = evidence.location
            key = (
                location.path,
                location.start_line,
                location.end_line,
                location.json_pointer,
                location.config_key,
            )
            if key in seen:
                continue
            seen.add(key)
            locations.append(location.model_copy(deep=True))
        return tuple(locations)
