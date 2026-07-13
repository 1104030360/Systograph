from __future__ import annotations

import inspect
from importlib import import_module
from pathlib import Path

import pytest

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.reference_map_overlay_projector import (
    ReferenceMapOverlayProjector,
)
from kai_mind.core.services.system_map_index import SystemMapIndex
from kai_mind.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)

V1_RICH_MAP = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "valid_rich_frontend_sample.v1.json"
)


@pytest.fixture
def canonical_map() -> AiSystemMapV2:
    legacy = RagSystemMap.model_validate_json(
        V1_RICH_MAP.read_text(encoding="utf-8")
    )
    return SystemMapV1ToV2Adapter().adapt_to_canonical(legacy)


def test_reference_overlay_projector_contract_is_available() -> None:
    # Given
    module_name = "kai_mind.core.services.reference_map_overlay_projector"

    # When
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        pytest.fail(
            "ReferenceMapOverlayProjector module is not implemented",
            pytrace=False,
        )

    # Then
    assert hasattr(module, "ReferenceMapOverlayProjector")


def test_reference_overlay_projector_exposes_narrow_project_interface() -> (
    None
):
    # Given
    module = import_module(
        "kai_mind.core.services.reference_map_overlay_projector"
    )
    projector_type = module.ReferenceMapOverlayProjector

    # When
    signature = inspect.signature(projector_type.project)

    # Then
    assert list(signature.parameters) == [
        "self",
        "index",
        "profile_result",
        "node_ids_by_source",
    ]


def test_map_only_projection_emits_fixed_reference_catalog_as_undetermined(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    catalog = CapabilityReferenceMapLoader().load()
    index = SystemMapIndex.from_map(canonical_map)

    # When
    overlay = ReferenceMapOverlayProjector().project(
        index,
        profile_result=None,
        node_ids_by_source={},
    )

    # Then
    assert [node.reference_node_id for node in overlay.nodes] == [
        node.id for node in catalog.nodes
    ]
    assert all(
        node.semantic_kind == "reference_capability" for node in overlay.nodes
    )
    assert all(node.status == "undetermined" for node in overlay.nodes)
    assert all(
        node.activation
        == (
            "unknown"
            if catalog_node.activation_applicable
            else "not_applicable"
        )
        for node, catalog_node in zip(
            overlay.nodes,
            catalog.nodes,
            strict=True,
        )
    )


def test_profile_projection_surfaces_assessment_fields_without_recalculation(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    profile_result = ProfileInferenceService().infer(
        canonical_map,
        build_id="build:b1",
        scan_id="scan:s1",
        environment_id=canonical_map.environment_id,
    )
    index = SystemMapIndex.from_map(canonical_map)
    node_ids_by_source = {
        component.component_id: f"node:repo:{position}"
        for position, component in enumerate(canonical_map.components)
    }

    # When
    overlay = ReferenceMapOverlayProjector().project(
        index,
        profile_result=profile_result,
        node_ids_by_source=node_ids_by_source,
    )

    # Then
    reference_nodes = [
        node
        for node in overlay.nodes
        if node.semantic_kind == "reference_capability"
    ]
    assert len(reference_nodes) == 52
    assert all(
        node.status == assessment.status
        and node.activation == assessment.activation
        and tuple(node.evidence_ids) == assessment.evidence_ids
        and tuple(node.direct_evidence_ids) == assessment.direct_evidence_ids
        and tuple(node.indirect_evidence_ids)
        == assessment.indirect_evidence_ids
        and tuple(node.explicit_negative_evidence_ids)
        == assessment.explicit_negative_evidence_ids
        and tuple(node.related_component_ids)
        == assessment.related_component_ids
        for node, assessment in zip(
            reference_nodes,
            profile_result.reference_capability_assessments,
            strict=True,
        )
    )
    assert overlay.mapping_completeness is profile_result.mapping_completeness
    assert list(overlay.reference_assessments_by_id) == [
        item.reference_node_id
        for item in profile_result.reference_capability_assessments
    ]


def test_profile_attachments_use_only_explicit_reliable_anchors(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    profile_result = ProfileInferenceService().infer(
        canonical_map,
        build_id="build:b1",
        scan_id="scan:s1",
        environment_id=canonical_map.environment_id,
    )
    index = SystemMapIndex.from_map(canonical_map)
    node_ids_by_source = {
        **{
            component.component_id: f"node:repo:{position}"
            for position, component in enumerate(canonical_map.components)
        },
        **{
            component.unmapped_id: f"node:unmapped:{position}"
            for position, component in enumerate(
                canonical_map.unmapped_components
            )
        },
    }

    # When
    overlay = ReferenceMapOverlayProjector().project(
        index,
        profile_result=profile_result,
        node_ids_by_source=node_ids_by_source,
    )

    # Then
    profile_nodes = [
        node
        for node in overlay.nodes
        if node.semantic_kind == "profile_attachment"
    ]
    expected_profiles = [
        finding
        for finding in profile_result.profiles
        if any(
            source_id in node_ids_by_source
            for source_id in (
                *finding.related_component_ids,
                *finding.related_unmapped_component_ids,
            )
        )
    ]
    assert [node.profile_id for node in profile_nodes] == [
        finding.profile_id for finding in expected_profiles
    ]
    assert all(
        node.primary_anchor_node_id == node.anchor_node_ids[0]
        and set(node.anchor_node_ids) <= set(node_ids_by_source.values())
        for node in profile_nodes
    )
    assert list(overlay.profile_findings_by_id) == [
        finding.profile_id for finding in profile_result.profiles
    ]
    profile_filter = next(
        item
        for item in overlay.filters
        if item.id == "filter:profile_attachments"
    )
    assert profile_filter.active is False
    assert profile_filter.matches_node_ids == [
        node.id for node in profile_nodes
    ]
    topology_kinds = {relation.kind for relation in overlay.relationships}
    assert topology_kinds <= {
        "reference_component_mapping",
        "reference_unmapped_mapping",
        "reference_candidate_mapping",
        "profile_anchor",
        "candidate_source",
    }


def test_capability_candidate_is_distinct_and_anchors_related_profile(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    candidate = CapabilityCandidateComponent(
        id="capability-candidate:reranker",
        name="Reranker",
        observed_kind="reranker",
        evidence_ids=["evidence:code_pattern:reranker-ambiguous"],
        source_unmapped_component_id="unmapped:src-rag-rerank",
        source_file="src/rag/rerank.py",
    )
    profile_result = ProfileInferenceService().infer(
        canonical_map,
        build_id="build:b1",
        scan_id="scan:s1",
        environment_id=canonical_map.environment_id,
        capability_candidate_components=(candidate,),
    )
    node_ids_by_source = {
        **{
            component.component_id: f"node:repo:{position}"
            for position, component in enumerate(canonical_map.components)
        },
        "unmapped:src-rag-rerank": "node:unmapped:reranker",
    }

    # When
    overlay = ReferenceMapOverlayProjector().project(
        SystemMapIndex.from_map(canonical_map),
        profile_result=profile_result,
        node_ids_by_source=node_ids_by_source,
    )

    # Then
    candidate_node = next(
        node
        for node in overlay.nodes
        if node.semantic_kind == "capability_candidate"
    )
    assert candidate_node.source_id == candidate.id
    assert candidate_node.primary_anchor_node_id == ("node:unmapped:reranker")
    assert list(overlay.capability_candidates_by_id) == [candidate.id]
    reranking_profile = next(
        node for node in overlay.nodes if node.profile_id == "reranking"
    )
    assert candidate_node.id in reranking_profile.anchor_node_ids
    assert any(
        relation.kind == "candidate_source"
        and relation.source_node_id == candidate_node.id
        for relation in overlay.relationships
    )
    assert any(
        relation.kind == "reference_candidate_mapping"
        and relation.source_node_id == "node:reference:reranker"
        and relation.target_node_id == candidate_node.id
        for relation in overlay.relationships
    )
    profile_filter = next(
        item
        for item in overlay.filters
        if item.id == "filter:profile_attachments"
    )
    candidate_filter = next(
        item
        for item in overlay.filters
        if item.id == "filter:capability_candidates"
    )
    assert candidate_node.id not in profile_filter.matches_node_ids
    assert candidate_filter.matches_node_ids == [candidate_node.id]
