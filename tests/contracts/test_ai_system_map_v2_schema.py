"""Contract tests for ai-system-map/v2 (00A expand phase)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from kai_mind.core.models.ai_system_map_v2 import (
    REFERENCE_NODE_COUNT,
    REFERENCE_PLANE_IDS,
    AiSystemMapV2,
    AssessmentStatus,
    CapabilityAssessment,
    GroundingReadiness,
    ReferenceCapabilityOverlay,
    ReferenceMapCatalog,
    build_ai_system_map_v2_schema,
)
from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationError,
    SystemMapV2ValidationService,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ai_system_map" / "v2"
SCHEMA_PATH = (
    Path(__file__).parents[2] / "schemas" / "ai-system-map.v2.schema.json"
)


def load_fixture(name: str) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8")),
    )


def load_schema() -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
    )


def assert_valid_v2_contract(data: dict[str, Any]) -> AiSystemMapV2:
    AiSystemMapV2.model_validate(data)
    Draft202012Validator(load_schema()).validate(data)
    return SystemMapV2ValidationService().validate(data)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "grounded_rag.v2.json",
        "non_grounded_llm_app.v2.json",
        "tool_using_agent.v2.json",
        "workflow_graph.v2.json",
    ],
)
def test_v2_fixtures_satisfy_ai_system_map_contract(fixture_name: str) -> None:
    data = load_fixture(fixture_name)

    system_map = assert_valid_v2_contract(data)

    assert system_map.schema_version == "ai-system-map/v2"
    assert system_map.system_type == "ai_system"
    assert "confidence" not in json.dumps(data)
    assert "profiles" not in data
    assert "release_verdict" not in data


def test_non_grounded_llm_app_is_not_forced_into_rag_slots() -> None:
    system_map = assert_valid_v2_contract(
        load_fixture("non_grounded_llm_app.v2.json")
    )

    layers = {component.layer for component in system_map.components}
    assert "retrieval" not in layers
    assert any(
        component.canonical_type == "llm"
        for component in system_map.components
    )


def test_tool_using_agent_exposes_control_and_tool_components() -> None:
    system_map = assert_valid_v2_contract(
        load_fixture("tool_using_agent.v2.json")
    )

    types = {component.canonical_type for component in system_map.components}
    assert "agent_loop" in types
    assert "tool" in types


def test_workflow_graph_preserves_edges_without_rag_template() -> None:
    system_map = assert_valid_v2_contract(
        load_fixture("workflow_graph.v2.json")
    )

    assert len(system_map.edges) >= 1
    assert all(
        edge.source.startswith("component:") for edge in system_map.edges
    )
    assert "components_by_slot" not in system_map.model_dump(mode="json")


def test_checked_in_v2_schema_matches_pydantic_generated_schema() -> None:
    assert load_schema() == build_ai_system_map_v2_schema()


def test_v2_schema_forbids_extra_and_rejects_confidence() -> None:
    data = load_fixture("grounded_rag.v2.json")
    data["confidence"] = 0.9

    with pytest.raises((ValidationError, SystemMapV2ValidationError)):
        SystemMapV2ValidationService().validate(data)


def test_reference_map_catalog_is_fixed_ten_planes_and_fifty_two_nodes() -> (
    None
):
    catalog = ReferenceMapCatalog.default()

    assert list(catalog.plane_ids) == list(REFERENCE_PLANE_IDS)
    assert catalog.node_count == REFERENCE_NODE_COUNT == 52
    assert len(catalog.nodes) == 52


def test_reference_overlay_rejects_copied_reference_node_ids() -> None:
    catalog = ReferenceMapCatalog.default()
    overlay = ReferenceCapabilityOverlay.model_validate(
        {
            "reference_map_version": catalog.version,
            "bindings": [
                {
                    "reference_node_id": "dense_retriever",
                    "component_ids": [
                        "component:retriever:qdrant",
                    ],
                }
            ],
        }
    )

    catalog.validate_overlay(overlay)
    copied_ids = {
        component_id
        for binding in overlay.bindings
        for component_id in binding.component_ids
    }
    assert "dense_retriever" not in copied_ids


def test_not_detected_requires_coverage_gate() -> None:
    assessment = CapabilityAssessment.model_validate(
        {
            "reference_node_id": "web_retriever",
            "plane_id": "retrieval",
            "status": "not_detected",
            "activation": "unknown",
            "semantic_kind": "reference_capability",
            "evidence_ids": [],
            "build_id": "build:test",
            "scan_id": "scan:test",
            "environment_id": "environment:default-static",
            "not_detected_coverage_gate_passed": False,
        }
    )

    with pytest.raises(SystemMapV2ValidationError):
        SystemMapV2ValidationService().validate_assessment(assessment)


def test_detected_requires_direct_evidence_kind() -> None:
    assessment = CapabilityAssessment.model_validate(
        {
            "reference_node_id": "llm_answerer",
            "plane_id": "generation",
            "status": "detected",
            "activation": "enabled",
            "semantic_kind": "reference_capability",
            "evidence_ids": ["evidence:llm"],
            "evidence_kinds": {"evidence:llm": "indirect"},
            "build_id": "build:test",
            "scan_id": "scan:test",
            "environment_id": "environment:default-static",
        }
    )

    with pytest.raises(SystemMapV2ValidationError):
        SystemMapV2ValidationService().validate_assessment(assessment)


def test_assessment_status_literals_are_five_state() -> None:
    assert set(get_args(AssessmentStatus)) == {
        "detected",
        "partial",
        "undetermined",
        "not_detected",
        "conflicted",
    }


def test_grounding_readiness_is_derived_projection_not_canonical_truth() -> (
    None
):
    readiness = GroundingReadiness.model_validate(
        {
            "status": "partial",
            "missing_signals": ["citation_mapper"],
            "related_component_ids": ["component:retriever:qdrant"],
            "evidence_ids": ["evidence:retriever"],
        }
    )

    assert readiness.status == "partial"
    dumped = readiness.model_dump(mode="json")
    assert "confidence" not in dumped
    assert "release_verdict" not in dumped
