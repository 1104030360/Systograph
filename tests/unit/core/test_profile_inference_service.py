from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
)
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.services import profile_inference_service
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    MVP_CAPABILITY_PROFILE_IDS,
    ProfileInferenceService,
)

FIXTURE_DIR = Path("tests/fixtures/ai_system_map/v2")


def load_map(name: str) -> AiSystemMapV2:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return CanonicalMapLoader().load(payload).normalized


def infer(name: str) -> ProfileInferenceResult:
    system_map = load_map(name)
    return ProfileInferenceService().infer(
        system_map,
        build_id=system_map.build_id or "build:test",
        scan_id=system_map.scan_id or "scan:test",
        environment_id=system_map.environment_id,
    )


def map_with_signals(
    component_types: tuple[str, ...],
    *,
    relationship: str | None = None,
    explicit_negative_nodes: tuple[str, ...] = (),
) -> AiSystemMapV2:
    base = load_map("non_grounded_llm_app.v2.json")
    evidence = [
        CanonicalEvidence(
            evidence_id=f"evidence:{component_type}:{index}",
            artifact_type="python",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(
                path=f"src/{component_type}.py",
                start_line=1,
            ),
            rule_id=f"test.{component_type}",
        )
        for index, component_type in enumerate(component_types)
    ]
    components = [
        CanonicalComponent(
            component_id=f"component:{component_type}:{index}",
            display_name=component_type.replace("_", " ").title(),
            canonical_type=component_type,
            layer="undetermined",
            status="detected",
            activation="enabled",
            evidence_ids=[evidence[index].evidence_id],
            metadata={},
        )
        for index, component_type in enumerate(component_types)
    ]
    negative_evidence = [
        CanonicalEvidence(
            evidence_id=f"evidence:coverage:{node_id}",
            artifact_type="coverage",
            evidence_kind="explicit_negative",
            location=CanonicalEvidenceLocation(),
            rule_id=f"coverage.reference.{node_id}",
        )
        for node_id in explicit_negative_nodes
    ]
    edges = []
    if relationship is not None and components:
        edges.append(
            CanonicalEdge(
                edge_id=f"edge:{relationship}",
                source=components[0].component_id,
                target=components[-1].component_id,
                relationship=relationship,
                status="observed",
                evidence_ids=[evidence[0].evidence_id],
            )
        )
    return base.model_copy(
        update={
            "components": components,
            "edges": edges,
            "evidence": [*evidence, *negative_evidence],
            "risk_hints": [],
            "unmapped_components": [],
        }
    )


def test_inference_emits_complete_reference_and_profile_checklists() -> None:
    result = infer("grounded_rag.v2.json")

    assert len(result.reference_capability_assessments) == 52
    assert (
        len(
            {
                item.reference_node_id
                for item in result.reference_capability_assessments
            }
        )
        == 52
    )
    assert {profile.profile_id for profile in result.profiles} == set(
        MVP_CAPABILITY_PROFILE_IDS
    )
    assert result.mapping_completeness.denominator == 52
    assert (
        sum(result.mapping_completeness.status_counts.model_dump().values())
        == 52
    )


def test_grounded_rag_detects_grounding_without_mutating_map() -> None:
    system_map = load_map("grounded_rag.v2.json")
    before = system_map.model_dump(mode="json")

    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:grounded-rag",
        scan_id="scan:grounded-rag",
        environment_id="environment:default-static",
    )

    profiles = {profile.profile_id: profile for profile in result.profiles}
    assert profiles["rag-grounding"].status == "detected"
    assert profiles["rag-grounding"].direct_evidence_ids
    assert system_map.model_dump(mode="json") == before


def test_tool_agent_detects_agentic_control_and_tool_calling() -> None:
    result = infer("tool_using_agent.v2.json")
    profiles = {profile.profile_id: profile for profile in result.profiles}

    assert profiles["agentic-control"].status == "detected"
    assert profiles["tool-calling"].status == "detected"


def test_plain_llm_grounding_stays_undetermined_without_coverage() -> None:
    result = infer("non_grounded_llm_app.v2.json")
    grounding = next(
        profile
        for profile in result.profiles
        if profile.profile_id == "rag-grounding"
    )

    assert grounding.status == "undetermined"
    assert grounding.not_detected_coverage_gate_passed is False


def test_confirmed_reranker_candidate_stays_below_detected() -> None:
    system_map = load_map("grounded_rag.v2.json")
    candidate = CapabilityCandidateComponent(
        id="capability-candidate:reranker",
        name="Reranker",
        observed_kind="reranker",
        evidence_ids=["evidence:retriever"],
        source_unmapped_component_id="unmapped:reranker",
    )

    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:grounded-rag",
        scan_id="scan:grounded-rag",
        environment_id="environment:default-static",
        capability_candidate_components=(candidate,),
    )

    assessment = next(
        item
        for item in result.reference_capability_assessments
        if item.reference_node_id == "reranker"
    )
    profile = next(
        item for item in result.profiles if item.profile_id == "reranking"
    )
    assert assessment.status == "partial"
    assert profile.status == "partial"
    assert profile.related_capability_candidate_component_ids == (
        "capability-candidate:reranker",
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
    system_map = map_with_signals(
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
    system_map = map_with_signals(component_types)

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
    system_map = map_with_signals(
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
    system_map = map_with_signals(
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


def test_inference_has_no_manual_mapping_or_provider_dependency() -> None:
    source = inspect.getsource(profile_inference_service)

    assert "manual_mapping" not in source
    assert "llm_proposal" not in source
