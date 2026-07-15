from __future__ import annotations

import inspect
from importlib import resources
from typing import Never

import pytest

from kai_mind.core.services import capability_reference_map_loader
from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapError,
    CapabilityReferenceMapLoader,
)

EXPECTED_PLANES = (
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
)

EXPECTED_NODES_BY_PLANE = {
    "input_intent": ("user_input", "session_context", "query_classifier"),
    "control": (
        "planner",
        "router",
        "agent_loop",
        "orchestrator",
        "stop_policy",
        "human_approval_gate",
    ),
    "ingestion_indexing": (
        "document_loader",
        "parser",
        "chunker",
        "metadata_extractor",
        "embedder",
        "index_builder",
    ),
    "retrieval": (
        "dense_retriever",
        "sparse_retriever",
        "hybrid_retriever",
        "graph_retriever",
        "memory_retriever",
        "web_retriever",
    ),
    "extension_subsystems": (
        "graph_rag_system",
        "rag_anything_system",
        "infini_memory_system",
        "corag_federated_system",
    ),
    "evidence": (
        "reranker",
        "conflict_checker",
        "citation_mapper",
        "evidence_pack",
    ),
    "generation": (
        "context_composer",
        "prompt_builder",
        "llm_answerer",
        "tool_using_generator",
        "output_guardrail",
    ),
    "memory_state": (
        "session_state",
        "working_memory",
        "long_term_memory",
        "memory_reader",
        "memory_writer",
    ),
    "governance_observability": (
        "input_guardrail",
        "permission_policy",
        "human_approval",
        "trace_store",
        "eval_harness",
        "cost_monitor",
        "latency_monitor",
    ),
    "deployment_topology": (
        "client_app",
        "api_server",
        "agent_runtime",
        "worker_queue",
        "tool_network",
        "federated_clients",
    ),
}

MINIMAL_CATALOG = (
    'catalog_id = "ai-system-capability-reference-map"\n'
    'version = "1"\n'
    'display_name = "Test catalog"\n'
    'description = "Test-only metadata."\n\n'
    "[[planes]]\n"
    'id = "input_intent"\n'
    'label = "Input & Intent Plane"\n'
    'description = "Input metadata."\n'
    "display_order = 10\n\n"
    "[[nodes]]\n"
    'id = "user_input"\n'
    'plane_id = "input_intent"\n'
    'label = "User Input"\n'
    'description = "Input metadata."\n'
    "display_order = 10\n"
    "activation_applicable = true\n"
)


def test_loads_fixed_ten_plane_fifty_two_node_catalog() -> None:
    catalog = CapabilityReferenceMapLoader().load()

    assert catalog.catalog_id == "ai-system-capability-reference-map"
    assert catalog.version == "1"
    assert tuple(plane.id for plane in catalog.planes) == EXPECTED_PLANES
    assert len(catalog.nodes) == 52
    assert {
        plane_id: tuple(
            node.id for node in catalog.nodes if node.plane_id == plane_id
        )
        for plane_id in EXPECTED_PLANES
    } == EXPECTED_NODES_BY_PLANE


def test_catalog_nodes_have_one_known_plane_and_no_scanner_truth() -> None:
    catalog = CapabilityReferenceMapLoader().load()
    plane_ids = {plane.id for plane in catalog.planes}

    assert all(node.plane_id in plane_ids for node in catalog.nodes)
    assert all(
        node.activation_applicable in {True, False} for node in catalog.nodes
    )
    assert all(node.id not in {"pattern", "rule_id"} for node in catalog.nodes)


def test_parser_rejects_duplicate_plane_id() -> None:
    duplicate = MINIMAL_CATALOG + (
        "\n[[planes]]\n"
        'id = "input_intent"\n'
        'label = "Duplicate"\n'
        'description = "Duplicate metadata."\n'
        "display_order = 20\n"
    )

    with pytest.raises(
        CapabilityReferenceMapError, match="duplicate plane id"
    ):
        CapabilityReferenceMapLoader().parse_text(duplicate)


def test_parser_rejects_malformed_toml() -> None:
    # Given
    malformed = "[catalog"

    # When / Then
    with pytest.raises(
        CapabilityReferenceMapError,
        match="failed to parse capability catalog",
    ):
        CapabilityReferenceMapLoader().parse_text(malformed)


def test_parser_rejects_missing_required_catalog_fields() -> None:
    # Given
    missing_fields = 'catalog_id = "incomplete"\n'

    # When / Then
    with pytest.raises(CapabilityReferenceMapError, match="version"):
        CapabilityReferenceMapLoader().parse_text(missing_fields)


def test_loader_wraps_packaged_catalog_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    def unavailable(_package: str) -> Never:
        raise OSError("catalog unavailable")

    monkeypatch.setattr(
        resources,
        "files",
        unavailable,
    )

    # When / Then
    with pytest.raises(
        CapabilityReferenceMapError,
        match="failed to read packaged capability catalog",
    ):
        CapabilityReferenceMapLoader().load()


@pytest.mark.parametrize(
    ("field", "replacement", "match"),
    [
        ("catalog_id", "unexpected", "unexpected catalog_id"),
        ("version", "2", "unexpected catalog version"),
    ],
)
def test_loader_rejects_unexpected_packaged_catalog_identity(
    field: str,
    replacement: str,
    match: str,
) -> None:
    # Given
    loader = CapabilityReferenceMapLoader()
    invalid = loader.load().model_copy(update={field: replacement})

    # When / Then
    with pytest.raises(CapabilityReferenceMapError, match=match):
        loader._validate_active_catalog(invalid)


def test_loader_rejects_packaged_catalog_with_missing_plane() -> None:
    # Given
    loader = CapabilityReferenceMapLoader()
    catalog = loader.load()
    invalid = catalog.model_copy(update={"planes": catalog.planes[:-1]})

    # When / Then
    with pytest.raises(
        CapabilityReferenceMapError,
        match="catalog must contain 10 planes",
    ):
        loader._validate_active_catalog(invalid)


def test_loader_rejects_packaged_catalog_with_missing_node() -> None:
    # Given
    loader = CapabilityReferenceMapLoader()
    catalog = loader.load()
    invalid = catalog.model_copy(update={"nodes": catalog.nodes[:-1]})

    # When / Then
    with pytest.raises(
        CapabilityReferenceMapError,
        match="catalog must contain 52 nodes",
    ):
        loader._validate_active_catalog(invalid)


def test_parser_rejects_duplicate_node_id() -> None:
    duplicate = MINIMAL_CATALOG + (
        "\n[[nodes]]\n"
        'id = "user_input"\n'
        'plane_id = "input_intent"\n'
        'label = "Duplicate"\n'
        'description = "Duplicate metadata."\n'
        "display_order = 20\n"
        "activation_applicable = false\n"
    )

    with pytest.raises(CapabilityReferenceMapError, match="duplicate node id"):
        CapabilityReferenceMapLoader().parse_text(duplicate)


def test_parser_rejects_unknown_node_plane() -> None:
    invalid = MINIMAL_CATALOG.replace(
        'plane_id = "input_intent"',
        'plane_id = "missing_plane"',
    )

    with pytest.raises(CapabilityReferenceMapError, match="unknown plane_id"):
        CapabilityReferenceMapLoader().parse_text(invalid)


def test_parser_rejects_invalid_display_order() -> None:
    invalid = MINIMAL_CATALOG.replace(
        "display_order = 10", "display_order = 0", 1
    )

    with pytest.raises(CapabilityReferenceMapError, match="display_order"):
        CapabilityReferenceMapLoader().parse_text(invalid)


@pytest.mark.parametrize(
    "forbidden_key",
    (
        "pattern",
        "query",
        "condition",
        "threshold",
        "weight",
        "script",
        "hook",
        "detector",
    ),
)
def test_parser_rejects_executable_or_scoring_metadata(
    forbidden_key: str,
) -> None:
    invalid = MINIMAL_CATALOG.replace(
        "activation_applicable = true",
        f'activation_applicable = true\n{forbidden_key} = "forbidden"',
    )

    with pytest.raises(CapabilityReferenceMapError, match=forbidden_key):
        CapabilityReferenceMapLoader().parse_text(invalid)


def test_loader_has_no_target_repo_or_pipeline_dependency() -> None:
    source = inspect.getsource(capability_reference_map_loader)

    for forbidden_dependency in (
        "project_scan_service",
        "mapping_proposal",
        "manual_mapping",
        "llm_proposal",
        "query_trace",
        "web.routes",
    ):
        assert forbidden_dependency not in source


def test_loader_reads_only_the_package_bundled_catalog() -> None:
    parameters = tuple(
        inspect.signature(CapabilityReferenceMapLoader.load).parameters
    )

    assert parameters == ("self",)
