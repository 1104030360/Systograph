from __future__ import annotations

from importlib import resources
from typing import Final, Never

import pytest

from systograph.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from systograph.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from systograph.core.services.capability_type_node_map_loader import (
    CapabilityTypeNodeMapError,
    CapabilityTypeNodeMapLoader,
)

# Full snapshot of the packaged canonical type -> reference node
# lookup: keys AND values. Pinning only the key set leaves silent
# re-targeting invisible -- `prompt_template = ["parser"]` names a
# real catalog node, so the fail-closed loader accepts it and the
# bridge-rule guard in test_bridge_reference_alignment.py cannot see
# it either (it only checks that each bridge kind reaches >= 1 node,
# and 30 of these 39 keys are not bridge kinds at all: they come
# from manual mappings and the v1 adapter). Changing the packaged
# TOML must therefore be a deliberate edit here too.
EXPECTED_CANONICAL_TYPE_NODES: Final[dict[str, tuple[str, ...]]] = {
    "agent_loop": ("agent_loop", "agent_runtime"),
    "api_input": ("user_input", "api_server"),
    "api_orchestrator": ("api_server",),
    "api_route": ("api_server",),
    "chunker": ("chunker",),
    "conflict_checker": ("conflict_checker",),
    "context_composer": ("context_composer",),
    "document_loader": ("document_loader",),
    "embedder": ("embedder",),
    "embedding_model": ("embedder",),
    "embedding_provider": ("embedder",),
    "external_llm": ("llm_answerer",),
    "external_llm_provider": ("llm_answerer",),
    "graph_retriever": ("graph_retriever",),
    "http_vector_store": ("index_builder",),
    "hybrid_retriever": ("hybrid_retriever",),
    "index_builder": ("index_builder",),
    "llm": ("llm_answerer",),
    "local_llm_runtime": ("llm_answerer",),
    "local_persistent_vector_store": ("index_builder",),
    "long_term_memory": ("long_term_memory",),
    "memory": ("long_term_memory",),
    "metadata_extractor": ("metadata_extractor",),
    "orchestrator": ("orchestrator",),
    "parser": ("parser",),
    "prompt_template": ("prompt_builder",),
    "query_classifier": ("query_classifier",),
    "rag_anything_system": ("rag_anything_system",),
    "reranker": ("reranker",),
    "retriever": ("dense_retriever",),
    "router": ("router",),
    "sparse_retriever": ("sparse_retriever",),
    "tool": ("tool_using_generator", "tool_network"),
    "vector_db": ("index_builder",),
    "vector_db_config": ("index_builder",),
    "vector_retriever": ("dense_retriever",),
    "vector_store": ("index_builder",),
    "worker_queue": ("worker_queue",),
    "workflow_node": ("orchestrator",),
}
EXPECTED_CANONICAL_TYPE_COUNT = 39

MINIMAL_MAP = '[canonical_type_nodes]\nretriever = ["dense_retriever"]\n'


@pytest.fixture(name="catalog")
def fixture_catalog() -> CapabilityReferenceCatalog:
    return CapabilityReferenceMapLoader().load()


def test_packaged_map_pins_every_canonical_type_and_node_tuple(
    catalog: CapabilityReferenceCatalog,
) -> None:
    # Given / When
    mapping = CapabilityTypeNodeMapLoader().load(catalog)

    # Then
    assert dict(mapping) == EXPECTED_CANONICAL_TYPE_NODES
    assert len(mapping) == EXPECTED_CANONICAL_TYPE_COUNT


def test_packaged_map_keeps_the_known_multi_node_entries(
    catalog: CapabilityReferenceCatalog,
) -> None:
    """Named record of the three deliberate one-type -> two-node rows.

    The snapshot above already compares these tuples; this test exists
    so the fan-outs stay an explicit, reviewable decision instead of
    three lines buried in a 39-row literal. Both members of each pair
    are real catalog nodes, so a reader cannot mistake them for a typo.
    """
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
