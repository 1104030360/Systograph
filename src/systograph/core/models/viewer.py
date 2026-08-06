# 這個檔案負責：前端 Viewer 用的圖投影契約（nodes / edges / filters / load
# result）。
# 注意：這是「投影結果」，不是 canonical map 真相；真相在 AiSystemMapV2。
#
# 呼叫鏈：
#   ViewerSessionService.load_map / build_canonical、BuildManifestService.load
#     → ViewerSessionService.build_loaded（唯一投影出口）
#     → GraphProjectionService.project(AiSystemMapV2) → GraphViewModel
#     → 包成 ViewerLoadResult
#   CLI: systograph validate-map → ViewerLoadResult
#   Web: build-scoped 讀取端點回 ViewerLoadResult；process-wide 讀圖已退役
#   MapBuildResult.viewer_load_result 也會帶一份
#   Frontend：types.ts / SystemGraph / DetailPanel / viewerStore 消費同形狀
# JSON
"""Viewer projection models derived from canonical ai-system-map/v2."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from systograph.core.models.profile_signal import MappingCompleteness


# 做什麼：前端 viewer payload 的基底（forbid extra、可用 alias、frozen）。
# 被誰用：本檔所有 Graph* / Viewer* model。
# 自己呼叫：Pydantic BaseModel。
class ViewerModel(BaseModel):
    """Base model for frontend-facing viewer payloads."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        frozen=True,
    )


# 做什麼：標明這個 graph node 的 assessment 屬於哪個 build/scan/environment。
# 被誰用：包在 GraphNodeModel.assessment_scope（尤其 reference / profile 節點）
# 。
# 內含：無巢狀 model。
class GraphAssessmentScopeModel(ViewerModel):
    build_id: str
    scan_id: str
    environment_id: str


# 做什麼：畫布上的一個節點（元件、reference capability、unmapped、profile…）。
# 被誰用：GraphViewModel.nodes；Frontend SystemGraph / DetailPanel。
# 內含：assessment_scope → GraphAssessmentScopeModel；各 evidence / related
# ids。
# 自己呼叫：無方法；由 GraphProjectionService / overlay 組出。
class GraphNodeModel(ViewerModel):
    id: str
    source_id: str | None = None
    reference_node_id: str | None = None
    component_id: str | None = None
    profile_id: str | None = None
    plane_id: str | None = None
    type: str | None = None
    semantic_kind: (
        Literal[
            "reference_capability",
            "repo_component",
            "unmapped_component",
            "capability_candidate",
            "profile_attachment",
        ]
        | None
    ) = None
    slot: str | None = None
    status: str | None = None
    activation: (
        Literal[
            "enabled",
            "disabled",
            "conditional",
            "unknown",
            "conflicted",
            "not_applicable",
        ]
        | None
    ) = None
    label: str
    subtitle: str | None = None
    badges: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    direct_evidence_ids: list[str] = Field(default_factory=list)
    indirect_evidence_ids: list[str] = Field(default_factory=list)
    explicit_negative_evidence_ids: list[str] = Field(default_factory=list)
    conflict_fields: list[dict[str, Any]] = Field(default_factory=list)
    not_detected_coverage_gate_passed: bool | None = None
    assessment_scope: GraphAssessmentScopeModel | None = None
    primary_anchor_node_id: str | None = None
    anchor_node_ids: list[str] = Field(default_factory=list)
    related_component_ids: list[str] = Field(default_factory=list)
    related_unmapped_component_ids: list[str] = Field(default_factory=list)
    related_capability_candidate_component_ids: list[str] = Field(
        default_factory=list
    )
    related_risk_hint_ids: list[str] = Field(default_factory=list)
    description: str | None = None
    implementation_depth_level: int | None = None
    implementation_depth_reason: str | None = None
    evidence_strength: str | None = None
    uncertainty: str | None = None
    recommended_next_checks: list[str] = Field(default_factory=list)
    risk_hint_ids: list[str] = Field(default_factory=list)


# 做什麼：畫布上的一條邊（from → to + relationship）。
# 被誰用：GraphViewModel.edges；Frontend SystemGraph。
# 注意：from_id 序列化成 JSON 欄位名 "from"（避開 Python 關鍵字）。
class GraphEdgeModel(ViewerModel):
    id: str
    source_id: str | None = None
    flow_id: str | None = None
    from_id: str = Field(
        serialization_alias="from",
        validation_alias="from",
    )
    to: str
    relationship: str | None = None
    label: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    risk_hint_ids: list[str] = Field(default_factory=list)


# 做什麼：非 flow 邊的語意關係（reference 對應、profile anchor、candidate
# source）。
# 被誰用：GraphViewModel.relationships；overlay / projection 掛導航用。
# 內含：source_node_id / target_node_id → GraphNodeModel.id。
class GraphRelationshipModel(ViewerModel):
    id: str
    kind: Literal[
        "reference_component_mapping",
        "reference_unmapped_mapping",
        "reference_candidate_mapping",
        "profile_anchor",
        "candidate_source",
    ]
    source_node_id: str
    target_node_id: str
    evidence_ids: list[str] = Field(default_factory=list)


# 做什麼：單一篩選器（點了會 highlight 哪些 node/edge）。
# 被誰用：包在 GraphFiltersModel.available；Frontend filter UI。
class GraphFilterModel(ViewerModel):
    id: str
    label: str
    kind: str
    active: bool = False
    matches_node_ids: list[str] = Field(default_factory=list)
    matches_edge_ids: list[str] = Field(default_factory=list)


# 做什麼：單一 lens（data/control/evidence/governance/source/risk 視角）。
# 被誰用：包在 GraphFiltersModel.lenses；GraphLensProjector 組出。
# 內含：matches_* 告訴前端這個 lens 會亮哪些節點/邊。
class GraphLensModel(ViewerModel):
    id: Literal[
        "lens:data",
        "lens:control",
        "lens:evidence",
        "lens:governance",
        "lens:source",
        "lens:risk",
    ]
    label: str
    supported: bool
    unavailable_reason: str | None = None
    matches_node_ids: list[str] = Field(default_factory=list)
    matches_edge_ids: list[str] = Field(default_factory=list)


# 做什麼：側欄詳情用的 lookup 表（點 node 後用 id 查 evidence / risk /
# profile…）。
# 被誰用：GraphViewModel.details；Frontend DetailPanel。
# 內含：多個 *_by_id dict（值是已序列化的 dict，方便前端直接顯示）。
class GraphDetailsModel(ViewerModel):
    evidence_by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)
    risk_hints_by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)
    reference_assessments_by_id: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )
    profile_findings_by_id: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )
    capability_candidates_by_id: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )


# 做什麼：公開 Markdown / readiness report 用的 endpoint 摘要。
# 被誰用：GraphViewModel.endpoints；GraphMarkdownRenderer。
class GraphEndpointModel(ViewerModel):
    endpoint_id: str
    value: str
    endpoint_type: Literal["local", "external"]
    method: str | None = None
    component_id: str | None = None
    slot: str | None = None


# 做什麼：canonical recommended next check（與 node profile 字串分開）。
# 被誰用：GraphViewModel.recommended_next_checks；GraphMarkdownRenderer。
class GraphRecommendedNextCheckModel(ViewerModel):
    id: str
    target_type: str
    target: str
    reason: str
    action: str


# 做什麼：整包 filters + lenses + 行為說明（例如 highlight）。
# 被誰用：GraphViewModel.filters；GraphProjection / graph_projection_filters。
# 內含：available → GraphFilterModel；lenses → GraphLensModel。
class GraphFiltersModel(ViewerModel):
    available: list[GraphFilterModel] = Field(default_factory=list)
    lenses: list[GraphLensModel] = Field(default_factory=list)
    behavior: str | None = None


# 做什麼：前端畫圖用的完整 view model（節點、邊、關係、詳情、篩選）。
# 被誰用：
#   - GraphProjectionService.project() 產出
#   - ViewerSessionService / GraphMarkdownRenderer
#   - Frontend SystemGraph、utils/graph.ts、types.ts
# 內含：nodes / edges / relationships / details / filters；
#       可選 mapping_completeness（來自 profile inference）；
#       additive endpoints / recommended_next_checks（Markdown）。
class GraphViewModel(ViewerModel):
    schema_version: str | None = None
    source_schema_version: str | None = None
    project_id: str | None = None
    scan_id: str | None = None
    build_id: str | None = None
    environment_id: str | None = None
    artifact_set_version: str | None = None
    generated_from_build_id: str | None = None
    reference_map_version: str | None = None
    mapping_completeness: MappingCompleteness | None = None
    map_json: str | None = None
    summary: dict[str, Any] | None = None
    nodes: list[GraphNodeModel]
    edges: list[GraphEdgeModel]
    relationships: list[GraphRelationshipModel] = Field(default_factory=list)
    endpoints: list[GraphEndpointModel] = Field(default_factory=list)
    recommended_next_checks: list[GraphRecommendedNextCheckModel] = Field(
        default_factory=list
    )
    details: GraphDetailsModel
    filters: GraphFiltersModel


# 做什麼：一次「載入 map 進 Viewer」的結果（成功/失敗 + 原始 map + graph）。
# 被誰用：
#   - ViewerSessionService.load_map / build_loaded / build_canonical / empty
#   - MapBuildResult.viewer_load_result
#   - Web API build-scoped 讀取端點直接回它
#     （MapBuildScopedResponse.viewer_load_result），沒有額外包裝層
# 內含：ai_system_map（dict）+ graph_view_model；loaded=False 時有
# error_reason。
# 注意：graph_view_model 一律投影自 canonical v2；ai_system_map 帶的是
# 來源文件原樣（legacy v1 讀取路徑時會是 v1 map）。
class ViewerLoadResult(ViewerModel):
    loaded: bool
    error_reason: str | None = None
    map_json: str | None = None
    ai_system_map: dict[str, Any]
    graph_view_model: GraphViewModel
