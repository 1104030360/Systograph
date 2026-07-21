from __future__ import annotations

import pytest
from tests.helpers.profile_inference import map_with_profile_signals

from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)


@pytest.mark.parametrize(
    ("profile_id", "component_types", "relationship"),
    [
        ("memory", ("long_term_memory",), None),
        ("workflow-orchestration", ("orchestrator",), "workflow_transition"),
        ("hybrid-retrieval", ("hybrid_retriever",), "retrieval_fusion"),
        ("reranking", ("reranker",), "rerank"),
        (
            "corrective-retrieval",
            ("conflict_checker", "router"),
            "fallback_route",
        ),
        (
            "self-reflection",
            ("conflict_checker", "agent_loop"),
            "self_critique",
        ),
        ("graph-retrieval", ("graph_retriever",), "graph_retrieval"),
        (
            "hierarchical-retrieval",
            ("index_builder", "context_composer"),
            "hierarchical_flow",
        ),
        (
            "contextual-retrieval",
            ("metadata_extractor", "context_composer"),
            "context_enrichment",
        ),
        (
            "multimodal-grounding",
            ("rag_anything_system",),
            "multimodal_retrieval",
        ),
        (
            "modular-composition",
            ("orchestrator", "router"),
            "component_selection",
        ),
        (
            "multi-query-retrieval",
            ("query_classifier", "router"),
            "query_route",
        ),
    ],
)
def test_profile_detects_only_from_direct_capability_and_wiring(
    profile_id: str,
    component_types: tuple[str, ...],
    relationship: str | None,
) -> None:
    system_map = map_with_profile_signals(
        component_types,
        relationship=relationship,
    )

    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:focused",
        scan_id="scan:focused",
        environment_id=system_map.environment_id,
    )
    profile = next(
        item for item in result.profiles if item.profile_id == profile_id
    )

    assert profile.status == "detected"
    assert profile.direct_evidence_ids


@pytest.mark.parametrize(
    ("profile_id", "component_types"),
    [
        ("reranking", ("reranker",)),
        ("graph-retrieval", ("graph_retriever",)),
        ("modular-composition", ("orchestrator", "router")),
    ],
)
def test_high_specificity_profile_requires_wiring(
    profile_id: str,
    component_types: tuple[str, ...],
) -> None:
    system_map = map_with_profile_signals(component_types)

    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:no-wiring",
        scan_id="scan:no-wiring",
        environment_id=system_map.environment_id,
    )
    profile = next(
        item for item in result.profiles if item.profile_id == profile_id
    )

    assert profile.status == "partial"


def test_explicit_reference_coverage_emits_not_detected() -> None:
    system_map = map_with_profile_signals(
        (),
        explicit_negative_nodes=("reranker",),
    )

    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:coverage",
        scan_id="scan:coverage",
        environment_id=system_map.environment_id,
    )
    assessment = next(
        item
        for item in result.reference_capability_assessments
        if item.reference_node_id == "reranker"
    )
    profile = next(
        item for item in result.profiles if item.profile_id == "reranking"
    )

    assert assessment.status == "not_detected"
    assert assessment.not_detected_coverage_gate_passed is True
    assert profile.status == "not_detected"
    assert profile.not_detected_coverage_gate_passed is True


def test_conflicting_positive_and_negative_evidence_is_field_specific() -> (
    None
):
    system_map = map_with_profile_signals(
        ("reranker",),
        relationship="rerank",
        explicit_negative_nodes=("reranker",),
    )

    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:conflict",
        scan_id="scan:conflict",
        environment_id=system_map.environment_id,
    )
    assessment = next(
        item
        for item in result.reference_capability_assessments
        if item.reference_node_id == "reranker"
    )
    profile = next(
        item for item in result.profiles if item.profile_id == "reranking"
    )

    assert assessment.status == "conflicted"
    assert assessment.conflict_fields[0].field == "status"
    assert profile.status == "conflicted"
    assert profile.conflict_fields
