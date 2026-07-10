from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.services.system_map_v1_to_v2_adapter import (
    LegacySystemMapAdaptError,
    SystemMapV1ToV2Adapter,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)

FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)


def _validated_rag_system_map() -> RagSystemMap:
    return SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )


def test_adapter_projects_validated_v1_map_into_generic_v2_view() -> None:
    system_map = _validated_rag_system_map()

    adapted = SystemMapV1ToV2Adapter().adapt(system_map)

    assert adapted.schema_version == "ai-system-map/v2"
    assert adapted.system_type == "ai_system"
    assert adapted.source_schema_version == "ai-system-map/v1"
    assert "release_verdict" not in adapted.model_dump(mode="json")
    assert "profiles" not in adapted.model_dump(mode="json")

    component_by_id = {
        component.component_id: component for component in adapted.components
    }
    vector_store = component_by_id["component:vector_store:qdrant"]
    assert vector_store.display_name == "Qdrant"
    assert vector_store.canonical_type == "vector_db"
    assert vector_store.layer == "retrieval"
    assert vector_store.status == "detected"
    assert vector_store.activation == "enabled"
    assert vector_store.metadata.legacy_slot == "vector_store"
    assert vector_store.metadata.semantic_kind == "repo_component"

    citation_placeholder = component_by_id[
        "component:slot_placeholder:citation_or_response_composer"
    ]
    assert citation_placeholder.canonical_type == "slot_placeholder"
    assert citation_placeholder.layer == "generation"
    assert citation_placeholder.status == "not_configured"
    assert citation_placeholder.activation == "disabled"
    assert citation_placeholder.metadata.semantic_kind == "slot_placeholder"

    legacy_extension = component_by_id["extension:cache:redis-response-cache"]
    assert legacy_extension.canonical_type == "legacy_extension"
    assert legacy_extension.layer == "extension_subsystems"
    assert legacy_extension.status == "confirmed"
    assert legacy_extension.activation == "enabled"
    assert legacy_extension.metadata.semantic_kind == "legacy_extension"

    candidate_by_id = {
        candidate.candidate_fact_id: candidate
        for candidate in adapted.candidate_facts
    }
    extension_candidate = candidate_by_id[
        "candidate:legacy_extension:extension:cache:redis-response-cache"
    ]
    assert extension_candidate.candidate_kind == "legacy_extension"
    assert (
        extension_candidate.source_component_id
        == "extension:cache:redis-response-cache"
    )
    assert extension_candidate.evidence_ids == ["evidence:dependency:redis"]

    endpoint_by_id = {
        endpoint.endpoint_id: endpoint for endpoint in adapted.endpoints
    }
    assert (
        endpoint_by_id["endpoint:local:qdrant"].component_id
        == "component:vector_store:qdrant"
    )

    risk_by_id = {risk.risk_id: risk for risk in adapted.risk_hints}
    missing_slot_risk = risk_by_id["risk:missing_required_slot:citation"]
    assert missing_slot_risk.target_type == "component"
    assert (
        missing_slot_risk.target
        == "component:slot_placeholder:citation_or_response_composer"
    )

    unmapped_by_id = {
        fact.unmapped_fact_id: fact for fact in adapted.unmapped_facts
    }
    reranker = unmapped_by_id["unmapped:src-rag-rerank"]
    assert reranker.observed_kind == "reranking_like_code"
    assert reranker.source_file == "src/rag/rerank.py"


def test_adapter_preserves_complete_evidence_collection() -> None:
    system_map = _validated_rag_system_map()

    adapted = SystemMapV1ToV2Adapter().adapt(system_map)

    source_evidence = [
        item.model_dump(mode="json") for item in system_map.evidence
    ]
    adapted_evidence = [
        item.model_dump(mode="json") for item in adapted.evidence
    ]
    assert adapted_evidence == source_evidence


def test_adapter_preserves_required_compatibility_fact_records() -> None:
    system_map = _validated_rag_system_map()

    adapted = SystemMapV1ToV2Adapter().adapt(system_map)

    source_component_ids = {
        instance.id
        for slot in system_map.components_by_slot.values()
        for instance in slot.instances
    } | {extension.id for extension in system_map.extensions}
    adapted_component_ids = {
        component.component_id
        for component in adapted.components
        if component.metadata.semantic_kind != "slot_placeholder"
    }
    assert adapted_component_ids == source_component_ids
    assert {edge.edge_id for edge in adapted.edges} == {
        edge.id for flow in system_map.flows for edge in flow.edges
    }
    assert {endpoint.endpoint_id for endpoint in adapted.endpoints} == {
        endpoint.id for endpoint in system_map.endpoints
    }
    assert {risk.risk_id for risk in adapted.risk_hints} == {
        risk.id for risk in system_map.risk_hints
    }
    assert {fact.unmapped_fact_id for fact in adapted.unmapped_facts} == {
        fact.id for fact in system_map.unmapped_components
    }


def test_adapter_preserves_multiple_instances_in_one_slot() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vector_store_slot = data["components_by_slot"]["vector_store"]
    secondary_instance = copy.deepcopy(vector_store_slot["instances"][0])
    secondary_instance.update(
        {
            "id": "component:vector_store:secondary",
            "name": "Secondary Vector Store",
            "provider": "secondary-provider",
            "evidence_ids": ["evidence:dependency:redis"],
        }
    )
    vector_store_slot["instances"].append(secondary_instance)
    target_edge = data["flows"][1]["edges"][2]
    target_edge["to_component_id"] = secondary_instance["id"]
    system_map = SystemMapValidationService().validate(data)

    adapted = SystemMapV1ToV2Adapter().adapt(system_map)

    source_instance_ids = sorted(
        item.id
        for item in system_map.components_by_slot["vector_store"].instances
    )
    adapted_instance_ids = sorted(
        item.component_id
        for item in adapted.components
        if item.metadata.legacy_slot == "vector_store"
        and item.metadata.semantic_kind == "repo_component"
    )
    assert adapted_instance_ids == source_instance_ids

    adapted_by_id = {item.component_id: item for item in adapted.components}
    assert adapted_by_id[secondary_instance["id"]].evidence_ids == [
        "evidence:dependency:redis"
    ]

    edge_by_id = {edge.edge_id: edge for edge in adapted.edges}
    assert edge_by_id[target_edge["id"]].target == secondary_instance["id"]


def test_adapter_resolves_slot_only_edges_without_mutating_input() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    target_edge = data["flows"][1]["edges"][2]
    assert target_edge["id"] == "edge:query_answer:retriever:vector_store"
    target_edge["from_component_id"] = None
    target_edge["to_component_id"] = None
    system_map = SystemMapValidationService().validate(data)
    before = copy.deepcopy(system_map.model_dump(mode="json"))

    adapted = SystemMapV1ToV2Adapter().adapt(system_map)

    edge_by_id = {edge.edge_id: edge for edge in adapted.edges}
    edge = edge_by_id["edge:query_answer:retriever:vector_store"]
    assert edge.source == "component:retriever:qdrant-retriever"
    assert edge.target == "component:vector_store:qdrant"
    assert system_map.model_dump(mode="json") == before


def test_adapter_rejects_dangling_edge_component_reference() -> None:
    system_map = _validated_rag_system_map()
    data = system_map.model_dump(mode="json")
    data["flows"][0]["edges"][0]["from_component_id"] = "component:missing"
    invalid_system_map = system_map.model_validate(data)

    with pytest.raises(LegacySystemMapAdaptError, match="component:missing"):
        SystemMapV1ToV2Adapter().adapt(invalid_system_map)


def test_adapt_to_canonical_keeps_evidence_ids_without_verdict() -> None:
    system_map = _validated_rag_system_map()

    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(system_map)

    assert canonical.schema_version == "ai-system-map/v2"
    assert canonical.system_type == "ai_system"
    assert canonical.source_schema_version == "ai-system-map/v1"
    assert {item.evidence_id for item in canonical.evidence} == {
        item.id for item in system_map.evidence
    }
    dumped = canonical.model_dump(mode="json")
    assert "release_verdict" not in dumped
    assert "profiles" not in dumped
    assert "active_output_remains_v1_until_plan_13" in (
        canonical.migration_warnings
    )


def test_adapter_is_deterministic_across_slot_key_order() -> None:
    original = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    reversed_data = copy.deepcopy(original)
    slots = reversed_data["components_by_slot"]
    reversed_data["components_by_slot"] = {
        key: slots[key] for key in reversed(list(slots.keys()))
    }
    original_map = SystemMapValidationService().validate(original)
    reversed_map = SystemMapValidationService().validate(reversed_data)

    first = SystemMapV1ToV2Adapter().adapt_to_canonical(original_map)
    second = SystemMapV1ToV2Adapter().adapt_to_canonical(reversed_map)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [item.component_id for item in first.components] == [
        item.component_id for item in second.components
    ]


def test_adapter_does_not_auto_confirm_unconfirmed_legacy_extension() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["extensions"] = [
        {
            "id": "extension:reranker:candidate",
            "name": "Reranker Candidate",
            "kind": "reranker",
            "status": "candidate",
            "confirmed_by_user": False,
            "description": "Pending confirmation.",
            "evidence_ids": ["evidence:dependency:redis"],
        }
    ]
    system_map = SystemMapValidationService().validate(data)

    adapted = SystemMapV1ToV2Adapter().adapt(system_map)
    canonical = SystemMapV1ToV2Adapter().to_canonical(adapted)

    extension = next(
        item
        for item in adapted.components
        if item.component_id == "extension:reranker:candidate"
    )
    assert extension.status == "undetermined"
    assert extension.activation == "unknown"
    assert extension.metadata.semantic_kind == "legacy_extension"

    candidate = next(
        item
        for item in adapted.candidate_facts
        if item.candidate_fact_id
        == "candidate:legacy_extension:extension:reranker:candidate"
    )
    assert candidate.metadata.confirmed_by_user is False
    assert candidate.metadata.source_status == "candidate"

    assert len(canonical.candidate_facts) == 1
    assert canonical.candidate_facts[0].metadata.confirmed_by_user is False
    canonical_extension = next(
        item
        for item in canonical.components
        if item.component_id == "extension:reranker:candidate"
    )
    assert canonical_extension.status == "undetermined"
    assert canonical_extension.activation == "unknown"


def test_adapter_keeps_confirmed_by_user_on_canonical_candidates() -> None:
    system_map = _validated_rag_system_map()

    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(system_map)

    candidate = next(
        item
        for item in canonical.candidate_facts
        if item.candidate_fact_id
        == ("candidate:legacy_extension:extension:cache:redis-response-cache")
    )
    assert candidate.metadata.confirmed_by_user is True
    extension = next(
        item
        for item in canonical.components
        if item.component_id == "extension:cache:redis-response-cache"
    )
    assert extension.status == "confirmed"
    assert extension.activation == "enabled"


def test_adapter_redacts_absolute_root_path_for_canonical_v2() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["project"]["root_path"] = "/Users/demo/sample-health-rag"
    data["project"]["path_mode"] = "absolute"
    system_map = SystemMapValidationService().validate(data)

    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(system_map)

    assert canonical.project.root_path is None
    assert (
        "absolute_root_path_redacted_for_canonical_v2"
        in canonical.migration_warnings
    )
