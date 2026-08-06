from __future__ import annotations

import importlib

from systograph.core.services.legacy_slot_layer_map import SLOT_LAYER_BY_ID

# The mapping is migration-only: the v1 -> v2 adapter is its sole
# consumer. The active v2 normalize path derives `layer` from
# canonical_type via CanonicalTypePlaneResolver and must never read this
# table again -- that retirement is asserted below.
CONSUMER_MODULES = ("systograph.core.services.system_map_v1_to_v2_adapter",)
RETIRED_CONSUMER_MODULES = (
    "systograph.core.services.system_map_v2_normalize_service",
)
# Frozen key space: the 13 `rag-core-v1` template slots, nothing else.
LEGACY_THIRTEEN_SLOTS = frozenset(
    {
        "app_api_or_orchestrator",
        "data_sources",
        "document_loader",
        "chunking",
        "embedding_model",
        "vector_store",
        "query_processing",
        "retriever",
        "prompt_builder",
        "llm",
        "citation_or_response_composer",
        "guardrails",
        "observability",
    }
)


def _bound_mapping(module_name: str) -> object:
    # Runtime reflection on purpose: the consumers only import the name,
    # so mypy strict (no implicit re-export) rightly refuses a direct
    # `from <consumer> import SLOT_LAYER_BY_ID` here.
    return vars(importlib.import_module(module_name)).get("SLOT_LAYER_BY_ID")


def test_migration_path_binds_the_owned_mapping_and_frozen_keyspace() -> None:
    """Given the table is now migration-only,
    When the v1 -> v2 adapter is imported,
    Then it binds the very object this module owns AND that object's key
    space is still exactly the 13 frozen `rag-core-v1` slots.

    Both halves matter now that only one consumer is left: the identity
    check alone would pass against any dict, so it says almost nothing
    on its own. Pinning the key space is what keeps the table frozen --
    a new canonical type belongs in `capability_type_node_map.toml`, not
    here.
    """
    # Given / When / Then
    for module_name in CONSUMER_MODULES:
        assert _bound_mapping(module_name) is SLOT_LAYER_BY_ID
    assert set(SLOT_LAYER_BY_ID) == LEGACY_THIRTEEN_SLOTS
    assert len(SLOT_LAYER_BY_ID) == 13


def test_active_v2_path_no_longer_imports_the_slot_layer_map() -> None:
    """Given the projection plane now comes from canonical_type,
    When the active v2 normalize module is imported,
    Then it binds no reference to the legacy slot -> layer table, so a
    mis-filed slot cannot reach the plane through a back door.
    """
    for module_name in RETIRED_CONSUMER_MODULES:
        assert _bound_mapping(module_name) is None
