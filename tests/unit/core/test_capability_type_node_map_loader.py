from __future__ import annotations

from importlib import resources
from typing import Never

import pytest

from kai_mind.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from kai_mind.core.services.capability_type_node_map_loader import (
    CapabilityTypeNodeMapError,
    CapabilityTypeNodeMapLoader,
)

# Snapshot of every canonical component type the assessment lookup
# knows about. Dropping one entry from the packaged TOML must turn
# this test red; the bridge-rule guard test cannot see the manual
# mapping and v1-adapter only keys.
EXPECTED_CANONICAL_TYPES = frozenset(
    {
        "agent_loop",
        "api_input",
        "api_orchestrator",
        "api_route",
        "chunker",
        "conflict_checker",
        "context_composer",
        "document_loader",
        "embedder",
        "embedding_model",
        "embedding_provider",
        "external_llm",
        "external_llm_provider",
        "graph_retriever",
        "http_vector_store",
        "hybrid_retriever",
        "index_builder",
        "llm",
        "local_llm_runtime",
        "local_persistent_vector_store",
        "long_term_memory",
        "memory",
        "metadata_extractor",
        "orchestrator",
        "parser",
        "prompt_template",
        "query_classifier",
        "rag_anything_system",
        "reranker",
        "retriever",
        "router",
        "sparse_retriever",
        "tool",
        "vector_db",
        "vector_db_config",
        "vector_retriever",
        "vector_store",
        "worker_queue",
        "workflow_node",
    }
)
EXPECTED_CANONICAL_TYPE_COUNT = 39

MINIMAL_MAP = '[canonical_type_nodes]\nretriever = ["dense_retriever"]\n'


@pytest.fixture(name="catalog")
def fixture_catalog() -> CapabilityReferenceCatalog:
    return CapabilityReferenceMapLoader().load()


def test_packaged_map_pins_the_exact_canonical_type_key_set(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given / When
    mapping = CapabilityTypeNodeMapLoader().load(catalog)

    # Then
    assert set(mapping) == EXPECTED_CANONICAL_TYPES
    assert len(mapping) == EXPECTED_CANONICAL_TYPE_COUNT


def test_packaged_map_keeps_the_known_multi_node_entries(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given / When
    mapping = CapabilityTypeNodeMapLoader().load(catalog)

    # Then
    assert mapping["agent_loop"] == ("agent_loop", "agent_runtime")
    assert mapping["api_input"] == ("user_input", "api_server")
    assert mapping["tool"] == ("tool_using_generator", "tool_network")


def test_parse_text_rejects_node_id_outside_the_catalog(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    invalid = MINIMAL_MAP.replace("dense_retriever", "not_a_catalog_node")

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="unknown reference node id 'not_a_catalog_node'",
    ):
        CapabilityTypeNodeMapLoader().parse_text(invalid, catalog)


def test_parse_text_rejects_empty_mapping(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    empty = "[canonical_type_nodes]\n"

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="must be a non-empty table",
    ):
        CapabilityTypeNodeMapLoader().parse_text(empty, catalog)


def test_parse_text_rejects_missing_mapping_section(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    missing = "# no mapping section at all\n"

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="must be a non-empty table",
    ):
        CapabilityTypeNodeMapLoader().parse_text(missing, catalog)


def test_parse_text_rejects_non_list_value(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    invalid = '[canonical_type_nodes]\nretriever = "dense_retriever"\n'

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="retriever must be a non-empty list of node ids",
    ):
        CapabilityTypeNodeMapLoader().parse_text(invalid, catalog)


def test_parse_text_rejects_empty_node_list(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    invalid = "[canonical_type_nodes]\nretriever = []\n"

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="retriever must be a non-empty list of node ids",
    ):
        CapabilityTypeNodeMapLoader().parse_text(invalid, catalog)


def test_parse_text_rejects_blank_node_id(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    invalid = '[canonical_type_nodes]\nretriever = [" "]\n'

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="retriever must be a non-empty list of node ids",
    ):
        CapabilityTypeNodeMapLoader().parse_text(invalid, catalog)


def test_parse_text_rejects_unknown_section(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    invalid = MINIMAL_MAP + '\n[legacy_slot_nodes]\nllm = ["llm_answerer"]\n'

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="unknown section: legacy_slot_nodes",
    ):
        CapabilityTypeNodeMapLoader().parse_text(invalid, catalog)


def test_parse_text_rejects_duplicate_canonical_type_key(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given: tomllib rejects duplicate keys natively.
    duplicate = MINIMAL_MAP + 'retriever = ["sparse_retriever"]\n'

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="failed to parse capability_type_node_map.toml",
    ):
        CapabilityTypeNodeMapLoader().parse_text(duplicate, catalog)


def test_parse_text_rejects_malformed_toml(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given
    malformed = "[canonical_type_nodes"

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="failed to parse capability_type_node_map.toml",
    ):
        CapabilityTypeNodeMapLoader().parse_text(malformed, catalog)


def test_load_wraps_packaged_map_read_error(
    catalog: CapabilityReferenceCatalog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    def unavailable(_package: str) -> Never:
        raise OSError("mapping unavailable")

    monkeypatch.setattr(resources, "files", unavailable)

    # When / Then
    with pytest.raises(
        CapabilityTypeNodeMapError,
        match="failed to read packaged capability_type_node_map.toml",
    ):
        CapabilityTypeNodeMapLoader().load(catalog)
