from __future__ import annotations

import inspect

from tests.helpers.profile_inference import (
    infer_profile_fixture,
    load_profile_map,
)

from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.services import profile_inference_service
from kai_mind.core.services.profile_inference_service import (
    MVP_CAPABILITY_PROFILE_IDS,
    ProfileInferenceService,
)


def test_inference_emits_complete_reference_and_profile_checklists() -> None:
    result = infer_profile_fixture("grounded_rag.v2.json")

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
    system_map = load_profile_map("grounded_rag.v2.json")
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
    result = infer_profile_fixture("tool_using_agent.v2.json")
    profiles = {profile.profile_id: profile for profile in result.profiles}

    assert profiles["agentic-control"].status == "detected"
    assert profiles["tool-calling"].status == "detected"


def test_plain_llm_grounding_stays_undetermined_without_coverage() -> None:
    result = infer_profile_fixture("non_grounded_llm_app.v2.json")
    grounding = next(
        profile
        for profile in result.profiles
        if profile.profile_id == "rag-grounding"
    )

    assert grounding.status == "undetermined"
    assert grounding.not_detected_coverage_gate_passed is False


def test_confirmed_reranker_candidate_stays_below_detected() -> None:
    system_map = load_profile_map("grounded_rag.v2.json")
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


def test_inference_has_no_manual_mapping_or_provider_dependency() -> None:
    source = inspect.getsource(profile_inference_service)

    assert "manual_mapping" not in source
    assert "llm_proposal" not in source
