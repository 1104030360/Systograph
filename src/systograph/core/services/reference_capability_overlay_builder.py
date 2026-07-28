# 這個檔案負責：把固定的 reference capability catalog（52 nodes）
# 投影成 graph overlay 節點，並（若有 profile）掛上對 component / unmapped /
# candidate 的關係。
# 不做 assessment 計算；只「顯示」profile_result 裡已有的評估結果。
#
# 呼叫鏈：
#   GraphProjectionService.project()
#     → ReferenceMapOverlayProjector.project(...)
#         → build_reference_capability_overlay(catalog, context)
#         → 回傳 (reference GraphNodeModel*, GraphRelationshipModel*)
#     → 與 base nodes / profile attachment overlay 合併進 GraphViewModel
from __future__ import annotations

from systograph.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from systograph.core.models.viewer import (
    GraphAssessmentScopeModel,
    GraphNodeModel,
    GraphRelationshipModel,
)
from systograph.core.services.reference_overlay_context import (
    ReferenceOverlayContext,
)


# 做什麼：為 catalog 每個 reference node 建一個 graph node；
#         若有 profile_result，再依 assessment 掛 mapping relationships。
# 被誰呼叫：ReferenceMapOverlayProjector.project()。
# 自己呼叫：
#   - 讀 context.profile_result.reference_capability_assessments
#   - 無 assessment 時 status=undetermined；activation 依
# catalog_node.activation_applicable
#   - context.index.component_by_id / unmapped_by_id 驗證錨點真的存在
#   - context.node_ids_by_source 把 canonical id 轉成 base graph node id
# 回傳：(nodes, relationships)；relationships 在沒有 profile_result 時為空。
# 注意：不重算 capability status；也不會憑空發明拓樸 edges。
def build_reference_capability_overlay(
    catalog: CapabilityReferenceCatalog,
    context: ReferenceOverlayContext,
) -> tuple[tuple[GraphNodeModel, ...], tuple[GraphRelationshipModel, ...]]:
    profile_result = context.profile_result
    assessments = (
        {
            item.reference_node_id: item
            for item in profile_result.reference_capability_assessments
        }
        if profile_result is not None
        else {}
    )
    nodes: list[GraphNodeModel] = []
    for catalog_node in catalog.nodes:
        assessment = assessments.get(catalog_node.id)
        status = (
            assessment.status if assessment is not None else ("undetermined")
        )
        activation = (
            assessment.activation
            if assessment is not None
            else (
                "unknown"
                if catalog_node.activation_applicable
                else "not_applicable"
            )
        )
        nodes.append(
            GraphNodeModel(
                id=f"node:reference:{catalog_node.id}",
                source_id=catalog_node.id,
                reference_node_id=catalog_node.id,
                plane_id=catalog_node.plane_id,
                type="reference_capability",
                semantic_kind="reference_capability",
                status=status,
                activation=activation,
                label=catalog_node.label,
                subtitle=catalog_node.description,
                badges=[status, activation, catalog_node.plane_id],
                evidence_ids=(
                    list(assessment.evidence_ids)
                    if assessment is not None
                    else []
                ),
                direct_evidence_ids=(
                    list(assessment.direct_evidence_ids)
                    if assessment is not None
                    else []
                ),
                indirect_evidence_ids=(
                    list(assessment.indirect_evidence_ids)
                    if assessment is not None
                    else []
                ),
                explicit_negative_evidence_ids=(
                    list(assessment.explicit_negative_evidence_ids)
                    if assessment is not None
                    else []
                ),
                conflict_fields=(
                    [
                        item.model_dump(mode="json")
                        for item in assessment.conflict_fields
                    ]
                    if assessment is not None
                    else []
                ),
                not_detected_coverage_gate_passed=(
                    assessment.not_detected_coverage_gate_passed
                    if assessment is not None
                    else None
                ),
                assessment_scope=(
                    GraphAssessmentScopeModel(
                        build_id=assessment.build_id,
                        scan_id=assessment.scan_id,
                        environment_id=assessment.environment_id,
                    )
                    if assessment is not None
                    else None
                ),
                related_component_ids=(
                    list(assessment.related_component_ids)
                    if assessment is not None
                    else []
                ),
                related_unmapped_component_ids=(
                    list(assessment.related_unmapped_component_ids)
                    if assessment is not None
                    else []
                ),
                related_capability_candidate_component_ids=(
                    list(assessment.related_capability_candidate_component_ids)
                    if assessment is not None
                    else []
                ),
            )
        )
    relationships: list[GraphRelationshipModel] = []
    if profile_result is not None:
        candidate_ids = {
            candidate.id
            for candidate in profile_result.capability_candidate_components
        }
        for assessment in profile_result.reference_capability_assessments:
            for position, component_id in enumerate(
                assessment.related_component_ids
            ):
                if (
                    context.index.component_by_id(component_id) is None
                    or component_id not in context.node_ids_by_source
                ):
                    continue
                relationships.append(
                    GraphRelationshipModel(
                        id=(
                            "relation:reference-component:"
                            f"{assessment.reference_node_id}:{position}"
                        ),
                        kind="reference_component_mapping",
                        source_node_id=(
                            f"node:reference:{assessment.reference_node_id}"
                        ),
                        target_node_id=(
                            context.node_ids_by_source[component_id]
                        ),
                        evidence_ids=list(assessment.evidence_ids),
                    )
                )
            for position, unmapped_id in enumerate(
                assessment.related_unmapped_component_ids
            ):
                if (
                    context.index.unmapped_by_id(unmapped_id) is None
                    or unmapped_id not in context.node_ids_by_source
                ):
                    continue
                relationships.append(
                    GraphRelationshipModel(
                        id=(
                            "relation:reference-unmapped:"
                            f"{assessment.reference_node_id}:{position}"
                        ),
                        kind="reference_unmapped_mapping",
                        source_node_id=(
                            f"node:reference:{assessment.reference_node_id}"
                        ),
                        target_node_id=(
                            context.node_ids_by_source[unmapped_id]
                        ),
                        evidence_ids=list(assessment.evidence_ids),
                    )
                )
            for position, candidate_id in enumerate(
                assessment.related_capability_candidate_component_ids
            ):
                if candidate_id not in candidate_ids:
                    continue
                relationships.append(
                    GraphRelationshipModel(
                        id=(
                            "relation:reference-candidate:"
                            f"{assessment.reference_node_id}:{position}"
                        ),
                        kind="reference_candidate_mapping",
                        source_node_id=(
                            f"node:reference:{assessment.reference_node_id}"
                        ),
                        target_node_id=(
                            f"node:capability-candidate:{candidate_id}"
                        ),
                        evidence_ids=list(assessment.evidence_ids),
                    )
                )
    return tuple(nodes), tuple(relationships)
