# 這個檔案負責：ai-system-map/v2 的 Pydantic 契約（canonical + compatibility +
# 衍生投影）。
# 與 system_map.py（v1）的關係：
#   v1 RagSystemMap → SystemMapV1ToV2Adapter → 本檔的 Compatibility / Canonical
# models
#   下游請吃 CanonicalMapLoader 產出的 AiSystemMapV2，不要自己判斷
# schema_version。
#
# 呼叫鏈：
#   CanonicalMapLoader.load()
#     ├─ v1 → adapter → AiSystemMapV2
#     └─ v2 → SystemMapV2ValidationService → AiSystemMapV2
#   SystemMapIndex.from_map(AiSystemMapV2) → graph / detail scan / mapping /
# overlay
#   ProfileInference / Reference overlay → ReferenceMapCatalog /
# CapabilityAssessment
#   build_ai_system_map_v2_schema() → contracts 測試 / schema artifact
"""Canonical and compatibility models for ai-system-map/v2."""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from systograph.core.models.artifact_scope import (
    PHASE2_P0_ARTIFACT_SET_VERSION,
    ArtifactSetVersion,
)
from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.system_map import Evidence

# ---------------------------------------------------------------------------
# Shared literals
# ---------------------------------------------------------------------------

CompatibilitySchemaVersion = Literal["ai-system-map/v2"]
CompatibilitySystemType = Literal["ai_system"]
V2SchemaVersion = Literal["ai-system-map/v2"]
V2SystemType = Literal["ai_system"]

AssessmentStatus = Literal[
    "detected",
    "partial",
    "undetermined",
    "not_detected",
    "conflicted",
]
ActivationState = Literal[
    "enabled",
    "disabled",
    "conditional",
    "unknown",
    "conflicted",
    "not_applicable",
]
AssessmentEvidenceKind = Literal["direct", "indirect", "explicit_negative"]
DetectionStatus = Literal[
    "detected",
    "missing",
    "not_configured",
    "not_applicable",
    "confirmed",
    "partial",
    "undetermined",
]
EdgeObservationStatus = Literal["observed", "detected", "undetermined"]
EndpointTypeV2 = Literal["local", "external"]
RiskTargetTypeV2 = Literal["component", "endpoint", "evidence", "file"]
SemanticKind = Literal[
    "repo_component",
    "slot_placeholder",
    "legacy_extension",
    "reference_capability",
    "workflow_node",
]
# CanonicalLayer / CanonicalCandidateKind 是 canonical model 的欄位型別
# （CanonicalComponent.layer、CanonicalCandidateFact.candidate_kind），
# 不是 migration-only 型別；Plan 15 清掉下方 Compatibility/Generic 群時
# 不可一併刪除，所以名字不掛 Compatibility。
CanonicalLayer = Literal[
    "input_intent",
    "control",
    "ingestion_indexing",
    "retrieval",
    "extension_subsystems",
    "evidence",
    "generation",
    "memory_state",
    "governance_observability",
    "deployment_topology",
    "undetermined",
]
CanonicalCandidateKind = Literal["legacy_extension"]

CompatibilityActivation = ActivationState
CompatibilityComponentStatus = DetectionStatus
CompatibilityComponentSemanticKind = Literal[
    "repo_component",
    "slot_placeholder",
    "legacy_extension",
]
CompatibilityEdgeStatus = Literal["observed"]
CompatibilityEndpointType = EndpointTypeV2
CompatibilityRiskTargetType = RiskTargetTypeV2

V2_SCHEMA_VERSION: Final[V2SchemaVersion] = "ai-system-map/v2"
V2_SYSTEM_TYPE: Final[V2SystemType] = "ai_system"
DEFAULT_ENVIRONMENT_ID: Final[str] = "environment:default-static"
REFERENCE_MAP_VERSION: Final[str] = "1"
REFERENCE_PLANE_COUNT: Final[int] = 10
REFERENCE_NODE_COUNT: Final[int] = 52
JSON_SCHEMA_DRAFT: Final[str] = "https://json-schema.org/draft/2020-12/schema"
V2_SCHEMA_ID: Final[str] = (
    "https://systograph.local/schemas/ai-system-map.v2.schema.json"
)


# 做什麼：v2 契約基底；禁止未知欄位，且 frozen（建好不能改）。
# 被誰用：本檔幾乎所有 model 繼承它。
# 自己呼叫：Pydantic BaseModel。
class V2ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# 做什麼：compatibility view 專用基底（與 canonical 同規則，語意分層用）。
# 被誰用：下方 Generic* / AiSystemMapV2CompatibilityView。
# 自己呼叫：繼承 V2ContractModel。
class CompatibilityContractModel(V2ContractModel):
    pass


# ---------------------------------------------------------------------------
# Compatibility view (Plan 00 adapter output)
# ---------------------------------------------------------------------------


# 做什麼：compatibility view 的專案基本資訊。
# 被誰用：SystemMapV1ToV2Adapter 填入 AiSystemMapV2CompatibilityView.project。
# 內含：無巢狀 model。
class CompatibilityProject(CompatibilityContractModel):
    name: str
    root_path: str | None = None
    root_path_redacted: str | None = None
    path_mode: str | None = None


# 做什麼：GenericComponent 的 metadata（保留 v1 slot / extension 來源資訊）。
# 被誰用：包在 GenericComponent.metadata。
# 內含：無巢狀 model。
class GenericComponentMetadata(CompatibilityContractModel):
    legacy_slot: str | None = None
    source_component_id: str | None = None
    source_extension_id: str | None = None
    semantic_kind: CompatibilityComponentSemanticKind
    required_for_rag: bool | None = None
    source_status: str | None = None
    source_kind: str | None = None


# 做什麼：v1 → v2 搬運用的通用元件形狀。
# 被誰用：migration-only——僅 SystemMapV1ToV2Adapter 使用（包進
# AiSystemMapV2CompatibilityView.components）；Plan 15 隨 v1 read support
# 一併移除。
# 內含：metadata → GenericComponentMetadata；evidence_ids → Evidence。
class GenericComponent(CompatibilityContractModel):
    component_id: str
    display_name: str
    canonical_type: str
    layer: CanonicalLayer
    status: CompatibilityComponentStatus
    activation: CompatibilityActivation
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: GenericComponentMetadata


# 做什麼：GenericEdge 的 metadata（保留 v1 flow / slot 資訊）。
# 被誰用：包在 GenericEdge.metadata。
class GenericEdgeMetadata(CompatibilityContractModel):
    source_edge_id: str
    flow_id: str
    from_slot: str
    to_slot: str


# 做什麼：compatibility 邊（source/target 元件 + relationship）。
# 被誰用：AiSystemMapV2CompatibilityView.edges。
# 內含：metadata → GenericEdgeMetadata。
class GenericEdge(CompatibilityContractModel):
    edge_id: str
    source: str
    target: str
    relationship: str
    status: CompatibilityEdgeStatus
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: GenericEdgeMetadata


# 做什麼：GenericEndpoint 的 metadata（保留 v1 endpoint / slot 來源）。
# 被誰用：包在 GenericEndpoint.metadata。
class GenericEndpointMetadata(CompatibilityContractModel):
    source_endpoint_id: str
    legacy_slot: str | None = None
    source_component_id: str | None = None


# 做什麼：compatibility endpoint。
# 被誰用：AiSystemMapV2CompatibilityView.endpoints。
# 內含：metadata → GenericEndpointMetadata；evidence_id → Evidence。
class GenericEndpoint(CompatibilityContractModel):
    endpoint_id: str
    value: str
    endpoint_type: CompatibilityEndpointType
    method: str | None = None
    component_id: str | None = None
    evidence_id: str
    metadata: GenericEndpointMetadata


# 做什麼：GenericRiskHint 的 metadata（保留 v1 risk id / target）。
# 被誰用：包在 GenericRiskHint.metadata。
class GenericRiskHintMetadata(CompatibilityContractModel):
    source_risk_id: str
    source_target: str
    source_target_type: str


# 做什麼：compatibility 風險提示。
# 被誰用：AiSystemMapV2CompatibilityView.risk_hints。
# 內含：metadata → GenericRiskHintMetadata。
class GenericRiskHint(CompatibilityContractModel):
    risk_id: str
    type: str
    target: str
    target_type: CompatibilityRiskTargetType
    evidence_id: str
    rule_id: str
    rationale: str
    uncertainty: str | None = None
    severity_hint: str | None = None
    metadata: GenericRiskHintMetadata


# 做什麼：compatibility 未映射事實（對應 v1 UnmappedComponent）。
# 被誰用：AiSystemMapV2CompatibilityView.unmapped_facts。
class GenericUnmappedFact(CompatibilityContractModel):
    unmapped_fact_id: str
    observed_kind: str
    status: str
    reason: str
    source_file: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


# 做什麼：GenericCandidateFact 的 metadata（來自 legacy extension）。
# 被誰用：包在 GenericCandidateFact.metadata。
class GenericCandidateFactMetadata(CompatibilityContractModel):
    source_extension_id: str
    confirmed_by_user: bool | None = None
    source_status: str


# 做什麼：compatibility candidate fact（擴充元件候選）。
# 被誰用：AiSystemMapV2CompatibilityView.candidate_facts。
# 內含：metadata → GenericCandidateFactMetadata。
class GenericCandidateFact(CompatibilityContractModel):
    candidate_fact_id: str
    candidate_kind: CanonicalCandidateKind
    display_name: str
    source_component_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: GenericCandidateFactMetadata


# 做什麼：v1 → v2 中間 compatibility view 的根物件。
# 被誰用：migration-only——僅 SystemMapV1ToV2Adapter 使用（產出後再轉成正式
# AiSystemMapV2）；Plan 15 隨 v1 read support 一併移除。
# 內含：components / edges / evidence(v1 Evidence) / endpoints / risks /
# unmapped
# / candidates / recommended_next_checks。
# 注意：這裡的 evidence 仍用 v1 的 Evidence model（來自 system_map.py）；
# recommended_next_checks 用版本中立的 RecommendedNextCheck DTO 原樣搬運。
class AiSystemMapV2CompatibilityView(CompatibilityContractModel):
    schema_version: CompatibilitySchemaVersion = V2_SCHEMA_VERSION
    system_type: CompatibilitySystemType = V2_SYSTEM_TYPE
    source_schema_version: Literal["ai-system-map/v1"]
    project: CompatibilityProject
    components: list[GenericComponent] = Field(default_factory=list)
    edges: list[GenericEdge] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    endpoints: list[GenericEndpoint] = Field(default_factory=list)
    risk_hints: list[GenericRiskHint] = Field(default_factory=list)
    unmapped_facts: list[GenericUnmappedFact] = Field(default_factory=list)
    candidate_facts: list[GenericCandidateFact] = Field(default_factory=list)
    recommended_next_checks: list[RecommendedNextCheck] = Field(
        default_factory=list
    )


# ---------------------------------------------------------------------------
# Canonical ai-system-map/v2
# ---------------------------------------------------------------------------


# 做什麼：canonical map 的專案資訊（可有 project_id）。
# 被誰用：AiSystemMapV2.project；CanonicalMapLoader / validation。
class CanonicalProject(V2ContractModel):
    project_id: str | None = None
    name: str
    root_path: str | None = None
    root_path_redacted: str | None = None
    path_mode: str | None = None


# 做什麼：證據位置（檔案路徑、行號、json_pointer、config_key）。
# 被誰用：CanonicalEvidence.location；
# SystemMapIndex.related_locations_for_evidence_ids。
class CanonicalEvidenceLocation(V2ContractModel):
    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    json_pointer: str | None = None
    config_key: str | None = None


# 做什麼：canonical 證據（含 direct/indirect/explicit_negative）。
# 被誰用：AiSystemMapV2.evidence；SystemMapIndex；profile / capability
# assessment。
# 內含：location → CanonicalEvidenceLocation。
class CanonicalEvidence(V2ContractModel):
    evidence_id: str
    artifact_type: str
    evidence_kind: AssessmentEvidenceKind
    location: CanonicalEvidenceLocation
    extract_summary: str | None = None
    rule_id: str | None = None


# 做什麼：canonical 元件（扁平 list，不再用 v1 的 slot dict）。
# 被誰用：AiSystemMapV2.components；SystemMapIndex.component_by_id / by_type /
# by_layer。
# 內含：evidence_ids → CanonicalEvidence。
class CanonicalComponent(V2ContractModel):
    component_id: str
    display_name: str
    canonical_type: str
    layer: CanonicalLayer
    status: DetectionStatus
    activation: ActivationState
    evidence_ids: list[str] = Field(default_factory=list)
    framework: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# 做什麼：canonical 邊（source/target 指向 component_id）。
# 被誰用：AiSystemMapV2.edges；SystemMapIndex.outgoing/incoming_edges；profile
# wiring。
class CanonicalEdge(V2ContractModel):
    edge_id: str
    source: str
    target: str
    relationship: str
    status: EdgeObservationStatus
    evidence_ids: list[str] = Field(default_factory=list)
    undetermined_reason: str | None = None


# 做什麼：canonical endpoint。
# 被誰用：AiSystemMapV2.endpoints；SystemMapIndex.endpoint_by_id。
class CanonicalEndpoint(V2ContractModel):
    endpoint_id: str
    value: str
    endpoint_type: EndpointTypeV2
    method: str | None = None
    component_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


# 做什麼：canonical 風險提示。
# 被誰用：AiSystemMapV2.risk_hints；SystemMapIndex.risk_by_id；profile finding
# 掛關聯。
class CanonicalRiskHint(V2ContractModel):
    risk_id: str
    type: str
    target: str
    target_type: RiskTargetTypeV2
    evidence_id: str
    rule_id: str
    rationale: str
    uncertainty: str | None = None
    severity_hint: str | None = None


# 做什麼：canonical 未映射元件。
# 被誰用：AiSystemMapV2.unmapped_components；mapping proposal / evidence
# packet。
class CanonicalUnmappedComponent(V2ContractModel):
    unmapped_id: str
    observed_kind: str
    status: str
    reason: str
    source_file: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


# 做什麼：CanonicalCandidateFact 的 metadata。
# 被誰用：包在 CanonicalCandidateFact.metadata。
class CanonicalCandidateFactMetadata(V2ContractModel):
    source_extension_id: str
    confirmed_by_user: bool | None = None
    source_status: str


# 做什麼：canonical candidate fact（通常來自 legacy extension）。
# 被誰用：AiSystemMapV2.candidate_facts；SystemMapIndex.candidate_fact_by_id。
# 內含：metadata → CanonicalCandidateFactMetadata。
class CanonicalCandidateFact(V2ContractModel):
    candidate_fact_id: str
    candidate_kind: CanonicalCandidateKind
    display_name: str
    source_component_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: CanonicalCandidateFactMetadata


# 做什麼：canonical 建議下一步檢查（target + reason + action）。
# 被誰用：AiSystemMapV2.recommended_next_checks（正常 v2 build 直接產出）。
# 內含：無巢狀 model。
# 注意：欄位與 models/recommended_next_check.py 的版本中立 DTO 同形；
# SystemMapV2MaterializationService.materialize 呼叫
# RecommendedNextCheckService.derive，再由 SystemMapV2NormalizeService
# .assemble 轉成這個型別；v1 map 則由 SystemMapV1ToV2Adapter 原樣搬過來。
# Viewer / markdown 投影一律只讀這裡（v1、v2 同一條路）。
class CanonicalRecommendedNextCheck(V2ContractModel):
    id: str
    target_type: str
    target: str
    reason: str
    action: str


# 做什麼：正式的 canonical AI System Map 根物件（v2 真相來源）。
# 被誰用：CanonicalMapLoader 產出；SystemMapIndex / ProfileInference /
# GraphProjection
# /
#         DetailScan / Overlay / Validation 等下游一律吃這個。
# 內含：project + components/edges/evidence/endpoints/risks/unmapped/
# candidates/recommended_next_checks。
# 注意：schema_version / system_type 必須顯式出現在 JSON（不能靠 default 省略）
# 。
class AiSystemMapV2(V2ContractModel):
    # Artifact badges must be explicit in JSON; defaults would omit them from
    # generated JSON Schema `required` and let schema-only gates accept maps
    # that CanonicalMapLoader cannot load.
    schema_version: V2SchemaVersion
    system_type: V2SystemType
    scan_id: str | None = None
    build_id: str | None = None
    environment_id: str = DEFAULT_ENVIRONMENT_ID
    artifact_set_version: ArtifactSetVersion = PHASE2_P0_ARTIFACT_SET_VERSION
    generated_from_build_id: str | None = None
    source_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"] | (
        None
    ) = None
    migration_warnings: list[str] = Field(default_factory=list)
    project: CanonicalProject
    components: list[CanonicalComponent] = Field(default_factory=list)
    edges: list[CanonicalEdge] = Field(default_factory=list)
    evidence: list[CanonicalEvidence] = Field(default_factory=list)
    endpoints: list[CanonicalEndpoint] = Field(default_factory=list)
    risk_hints: list[CanonicalRiskHint] = Field(default_factory=list)
    unmapped_components: list[CanonicalUnmappedComponent] = Field(
        default_factory=list
    )
    candidate_facts: list[CanonicalCandidateFact] = Field(default_factory=list)
    # Additive optional field: it must stay out of the generated JSON Schema
    # `required` list so v2 artifacts published before this field existed keep
    # loading (missing → empty list).
    recommended_next_checks: list[CanonicalRecommendedNextCheck] = Field(
        default_factory=list
    )


# ---------------------------------------------------------------------------
# Assessment / reference map / derived projections
# ---------------------------------------------------------------------------


# 做什麼：某個欄位的證據衝突（兩邊各有一批 evidence）。
# 被誰用：包在 CapabilityAssessment.conflict_fields。
class FieldConflict(V2ContractModel):
    field_name: str
    evidence_ids_a: list[str] = Field(default_factory=list)
    evidence_ids_b: list[str] = Field(default_factory=list)


# 做什麼：單一 reference capability 的評估結果（52 個之一）。
# 被誰用：ReferenceCapabilityAssessmentService；之後再聚合成 ProfileFinding。
# 內含：conflict_fields → FieldConflict；evidence_ids → CanonicalEvidence。
# 注意：這是 assessment 結果，不是 canonical map 本身。
class CapabilityAssessment(V2ContractModel):
    reference_node_id: str
    plane_id: str
    status: AssessmentStatus
    activation: ActivationState
    semantic_kind: SemanticKind = "reference_capability"
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_kinds: dict[str, AssessmentEvidenceKind] = Field(
        default_factory=dict
    )
    conflict_fields: list[FieldConflict] = Field(default_factory=list)
    not_detected_coverage_gate_passed: bool | None = None
    build_id: str
    scan_id: str
    environment_id: str = DEFAULT_ENVIRONMENT_ID


# 做什麼：grounding readiness 的衍生投影（不是 canonical map 真相）。
# 被誰用：readiness report 相關路徑讀取。
# 內含：related_component_ids / evidence_ids 僅作導航。
class GroundingReadiness(V2ContractModel):
    """Derived projection for readiness findings — not canonical map truth."""

    status: AssessmentStatus
    missing_signals: list[str] = Field(default_factory=list)
    related_component_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


# 做什麼：reference map 裡的一個能力節點（如 dense_retriever）。
# 被誰用：ReferenceMapCatalog.nodes；來自 capability_reference_map.toml。
class ReferenceNode(V2ContractModel):
    reference_node_id: str
    plane_id: str
    activation_applicable: bool = True


# 做什麼：把 reference node 綁到實際 component_ids（overlay binding）。
# 被誰用：包在 ReferenceCapabilityOverlay.bindings。
class ReferenceOverlayBinding(V2ContractModel):
    reference_node_id: str
    component_ids: list[str] = Field(default_factory=list)


# 做什麼：reference capability overlay（哪個能力對應到哪些掃到的元件）。
# 被誰用：reference_map_overlay_projector / overlay builders；Viewer 疊圖。
# 內含：bindings → ReferenceOverlayBinding。
class ReferenceCapabilityOverlay(V2ContractModel):
    reference_map_version: str = REFERENCE_MAP_VERSION
    bindings: list[ReferenceOverlayBinding] = Field(default_factory=list)


# 做什麼：完整 reference map 目錄（10 planes、52 nodes）。
# 被誰用：capability assessment / overlay 驗證；ReferenceMapCatalog.default()
# 載入。
# 內含：nodes → ReferenceNode。
class ReferenceMapCatalog(V2ContractModel):
    version: str = REFERENCE_MAP_VERSION
    plane_ids: tuple[str, ...] = ()
    nodes: tuple[ReferenceNode, ...] = ()

    # 做什麼：從 packaged TOML 載入預設 catalog（10 planes / 52 nodes）。
    # 被誰呼叫：需要預設 reference map 的 service / 測試。
    # 自己呼叫：CapabilityReferenceMapLoader().load()，再轉成 ReferenceNode。
    @classmethod
    def default(cls) -> ReferenceMapCatalog:
        from systograph.core.services.capability_reference_map_loader import (
            CapabilityReferenceMapLoader,
        )

        catalog = CapabilityReferenceMapLoader().load()
        return cls(
            version=catalog.version,
            plane_ids=catalog.plane_ids,
            nodes=tuple(
                ReferenceNode(
                    reference_node_id=node.id,
                    plane_id=node.plane_id,
                    activation_applicable=node.activation_applicable,
                )
                for node in catalog.nodes
            ),
        )

    # 做什麼：回傳節點數量（通常應為 52）。
    # 被誰呼叫：測試 / 驗證邏輯讀取。
    @property
    def node_count(self) -> int:
        return len(self.nodes)

    # 做什麼：建構後檢查 catalog 形狀（planes=10、nodes=52、id 不重複）。
    # 被誰呼叫：Pydantic model_validator（建立 / validate 時自動跑）。
    # 自己呼叫：無外部 service。
    @model_validator(mode="after")
    def _validate_catalog_shape(self) -> ReferenceMapCatalog:
        if len(self.plane_ids) != REFERENCE_PLANE_COUNT:
            raise ValueError("reference map must contain exactly 10 planes")
        if len(self.plane_ids) != len(set(self.plane_ids)):
            raise ValueError("reference map plane ids must be unique")
        if len(self.nodes) != REFERENCE_NODE_COUNT:
            raise ValueError(
                f"reference map must contain exactly {REFERENCE_NODE_COUNT} "
                "nodes"
            )
        node_ids = {node.reference_node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("reference map node ids must be unique")
        if any(node.plane_id not in self.plane_ids for node in self.nodes):
            raise ValueError("reference map node has an unknown plane_id")
        return self

    # 做什麼：檢查 overlay 是否對得上這個 catalog（version、node id、不可自指）
    # 。
    # 被誰呼叫：overlay projector / builders 在套用 overlay 前。
    # 自己呼叫：無外部 service；只讀 self.nodes 與 overlay.bindings。
    def validate_overlay(self, overlay: ReferenceCapabilityOverlay) -> None:
        if overlay.reference_map_version != self.version:
            raise ValueError(
                "overlay reference_map_version does not match catalog"
            )
        known = {node.reference_node_id for node in self.nodes}
        for binding in overlay.bindings:
            if binding.reference_node_id not in known:
                raise ValueError(
                    f"unknown reference_node_id: {binding.reference_node_id}"
                )
            if binding.reference_node_id in binding.component_ids:
                raise ValueError(
                    "reference node id must not be copied as component id"
                )


# 做什麼：從 AiSystemMapV2 產出確定性 JSON Schema（給 contract / schema 檔用）
# 。
# 被誰呼叫：tests/contracts/test_ai_system_map_v2_schema.py、schema 產生流程。
# 自己呼叫：AiSystemMapV2.model_json_schema()，再補 $schema / $id。
def build_ai_system_map_v2_schema() -> dict[str, Any]:
    schema = AiSystemMapV2.model_json_schema()
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = V2_SCHEMA_ID
    return schema
