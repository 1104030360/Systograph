# 這個檔案負責：把 profile findings / capability candidates 投影成
# graph overlay 節點與關係（profile_attachment、capability_candidate）。
# 不做 profile 推論；只顯示 ProfileInferenceResult 裡已有結果，並錨到 base 圖。
#
# 呼叫鏈：
#   GraphProjectionService.project()
#     → ReferenceMapOverlayProjector.project(...)
#         → build_profile_attachment_overlay(context)
#         → 回傳 (nodes, relationships, filters)
#     → 與 reference overlay / base nodes 合併進 GraphViewModel
from __future__ import annotations

from kai_mind.core.models.viewer import (
    GraphAssessmentScopeModel,
    GraphFilterModel,
    GraphNodeModel,
    GraphRelationshipModel,
)
from kai_mind.core.services.reference_overlay_context import (
    ReferenceOverlayContext,
)


# 做什麼：
#   1) 為每個 capability_candidate 建節點，並（若有）連到來源 unmapped
#   2) 為每個 ProfileFinding 建 profile_attachment 節點，並連到可靠 anchors
#   3) 產出兩個 filter（profile_attachments / capability_candidates）
# 被誰呼叫：ReferenceMapOverlayProjector.project()。
# 自己呼叫：
#   - context.profile_result（無則只回空 nodes/relationships + 仍有兩個
# filter）
#   - context.node_ids_by_source / context.index 驗證 anchor 真的存在
# 錨點規則：
#   - candidate：source_unmapped 必須在 index 且在 node_ids_by_source
#   - profile：related component / unmapped / candidate 必須可解析成 graph
# node id
#   - 沒有任何可靠 anchor 的 profile → 跳過（不畫懸空 attachment）
# 注意：不重算 status；不會發明 topology edges（只用 GraphRelationship）。
def build_profile_attachment_overlay(
    context: ReferenceOverlayContext,
) -> tuple[
    tuple[GraphNodeModel, ...],
    tuple[GraphRelationshipModel, ...],
    tuple[GraphFilterModel, ...],
]:
    profile_result = context.profile_result
    nodes: list[GraphNodeModel] = []
    relationships: list[GraphRelationshipModel] = []
    candidate_node_ids: dict[str, str] = {}
    if profile_result is not None:
        for candidate in profile_result.capability_candidate_components:
            candidate_node_id = f"node:capability-candidate:{candidate.id}"
            candidate_node_ids[candidate.id] = candidate_node_id
            source_unmapped_id = candidate.source_unmapped_component_id
            anchor_node_id = (
                context.node_ids_by_source.get(source_unmapped_id)
                if source_unmapped_id is not None
                and context.index.unmapped_by_id(source_unmapped_id)
                is not None
                else None
            )
            nodes.append(
                GraphNodeModel(
                    id=candidate_node_id,
                    source_id=candidate.id,
                    type=candidate.observed_kind,
                    semantic_kind="capability_candidate",
                    status=candidate.status,
                    activation="unknown",
                    label=(
                        candidate.name
                        or candidate.observed_kind.replace("_", " ").title()
                    ),
                    subtitle="Capability candidate",
                    badges=[candidate.status, "candidate"],
                    evidence_ids=list(candidate.evidence_ids),
                    primary_anchor_node_id=anchor_node_id,
                    anchor_node_ids=(
                        [anchor_node_id] if anchor_node_id is not None else []
                    ),
                    related_unmapped_component_ids=(
                        [source_unmapped_id]
                        if source_unmapped_id is not None
                        else []
                    ),
                )
            )
            if anchor_node_id is not None:
                relationships.append(
                    GraphRelationshipModel(
                        id=f"relation:candidate-source:{candidate.id}",
                        kind="candidate_source",
                        source_node_id=candidate_node_id,
                        target_node_id=anchor_node_id,
                        evidence_ids=list(candidate.evidence_ids),
                    )
                )
        for finding in profile_result.profiles:
            anchor_source_ids = (
                *finding.related_component_ids,
                *finding.related_unmapped_component_ids,
                *finding.related_capability_candidate_component_ids,
            )
            anchor_node_ids = [
                (
                    candidate_node_ids[source_id]
                    if source_id in candidate_node_ids
                    else context.node_ids_by_source[source_id]
                )
                for source_id in anchor_source_ids
                if source_id in candidate_node_ids
                or (
                    source_id in context.node_ids_by_source
                    and (
                        context.index.component_by_id(source_id) is not None
                        or context.index.unmapped_by_id(source_id) is not None
                    )
                )
            ]
            if not anchor_node_ids:
                continue
            profile_node_id = f"node:profile-attachment:{finding.profile_id}"
            nodes.append(
                GraphNodeModel(
                    id=profile_node_id,
                    source_id=f"profile:{finding.profile_id}",
                    profile_id=finding.profile_id,
                    type="profile_attachment",
                    semantic_kind="profile_attachment",
                    status=finding.status,
                    activation=finding.activation,
                    label=finding.label,
                    subtitle=finding.description or "Capability overlay",
                    badges=[
                        finding.status,
                        finding.activation,
                        finding.primary_axis,
                    ],
                    evidence_ids=list(finding.evidence_ids),
                    direct_evidence_ids=list(finding.direct_evidence_ids),
                    indirect_evidence_ids=list(finding.indirect_evidence_ids),
                    explicit_negative_evidence_ids=list(
                        finding.explicit_negative_evidence_ids
                    ),
                    conflict_fields=[
                        item.model_dump(mode="json")
                        for item in finding.conflict_fields
                    ],
                    not_detected_coverage_gate_passed=(
                        finding.not_detected_coverage_gate_passed
                    ),
                    assessment_scope=GraphAssessmentScopeModel(
                        build_id=finding.build_id,
                        scan_id=finding.scan_id,
                        environment_id=finding.environment_id,
                    ),
                    primary_anchor_node_id=anchor_node_ids[0],
                    anchor_node_ids=anchor_node_ids,
                    related_component_ids=list(finding.related_component_ids),
                    related_unmapped_component_ids=list(
                        finding.related_unmapped_component_ids
                    ),
                    related_capability_candidate_component_ids=list(
                        finding.related_capability_candidate_component_ids
                    ),
                    related_risk_hint_ids=list(finding.related_risk_hint_ids),
                    description=finding.description,
                    implementation_depth_level=(
                        finding.implementation_depth_level
                    ),
                    implementation_depth_reason=(
                        finding.implementation_depth_reason
                    ),
                    evidence_strength=finding.evidence_strength,
                    uncertainty=finding.uncertainty,
                    recommended_next_checks=list(
                        finding.recommended_next_checks
                    ),
                    risk_hint_ids=list(finding.related_risk_hint_ids),
                )
            )
            relationships.extend(
                GraphRelationshipModel(
                    id=(
                        f"relation:profile-anchor:{finding.profile_id}:"
                        f"{position}"
                    ),
                    kind="profile_anchor",
                    source_node_id=profile_node_id,
                    target_node_id=anchor_node_id,
                    evidence_ids=list(finding.evidence_ids),
                )
                for position, anchor_node_id in enumerate(anchor_node_ids)
            )
    filters = (
        GraphFilterModel(
            id="filter:profile_attachments",
            label="Profile Attachments",
            kind="profile_attachment",
            active=False,
            matches_node_ids=[
                node.id
                for node in nodes
                if node.semantic_kind == "profile_attachment"
            ],
        ),
        GraphFilterModel(
            id="filter:capability_candidates",
            label="Capability Candidates",
            kind="capability_candidate",
            active=False,
            matches_node_ids=[
                node.id
                for node in nodes
                if node.semantic_kind == "capability_candidate"
            ],
        ),
    )
    return tuple(nodes), tuple(relationships), filters
