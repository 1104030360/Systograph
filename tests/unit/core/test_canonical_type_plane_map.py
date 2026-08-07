from __future__ import annotations

import pytest

from systograph.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from systograph.core.services.canonical_type_plane_map import (
    UNDETERMINED_PLANE,
    CanonicalTypePlaneError,
    CanonicalTypePlaneResolver,
)
from systograph.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from systograph.core.services.component_bridge_rules import (
    COMPONENT_BRIDGE_RULES,
)

# canonical_type values the config-path branch of ComponentBridgeRegistry
# emits. They never pass through COMPONENT_BRIDGE_RULES, so the rule
# sweep below cannot see them.
#
# MAINTENANCE: this list is hand-kept, unlike the COMPONENT_BRIDGE_RULES
# half which enumerates itself. The kinds below are string literals
# inside `_config_candidates()` (_vector_store_candidates /
# _llm_candidates / _openai_config_candidates) with no data structure to
# walk, so ADDING A CONFIG-PATH BRANCH MEANS ADDING ITS KIND HERE -- the
# coverage audit cannot notice a new one on its own.
CONFIG_PATH_COMPONENT_KINDS = (
    "vector_db_config",
    "local_llm_runtime",
    "external_llm_provider",
    "embedding_provider",
)


@pytest.fixture(name="catalog")
def fixture_catalog() -> CapabilityReferenceCatalog:
    return CapabilityReferenceMapLoader().load()


@pytest.fixture(name="resolver")
def fixture_resolver(
    catalog: CapabilityReferenceCatalog,
) -> CanonicalTypePlaneResolver:
    return CanonicalTypePlaneResolver(catalog=catalog)


def _bridge_component_kinds() -> tuple[str, ...]:
    """Every canonical_type the component bridge can emit."""
    return tuple(
        dict.fromkeys(
            (
                *(
                    spec.kind
                    for rule in COMPONENT_BRIDGE_RULES
                    for spec in rule.candidates
                ),
                *CONFIG_PATH_COMPONENT_KINDS,
            )
        )
    )


def test_single_node_type_takes_that_nodes_plane(
    resolver: CanonicalTypePlaneResolver,
) -> None:
    """Given a canonical type mapped to exactly one capability node,
    When the plane is resolved,
    Then it is the plane that node belongs to in the 52-node catalog.
    """
    # Given / When / Then
    assert resolver.plane_for("retriever") == "retrieval"
    assert resolver.plane_for("vector_db") == "ingestion_indexing"
    assert resolver.plane_for("prompt_template") == "generation"


def test_multi_node_type_takes_the_first_node_as_primary(
    resolver: CanonicalTypePlaneResolver,
) -> None:
    """Given a canonical type mapped to several capability nodes,
    When the plane is resolved,
    Then the first node in the TOML array decides the plane.

    `api_input = ["user_input", "api_server"]` spans two planes; the
    array order is the maintainer's primary-plane decision, so the
    answer must be `user_input`'s plane, never `api_server`'s.
    """
    # Given / When / Then
    assert resolver.plane_for("api_input") == "input_intent"
    assert resolver.plane_for("agent_loop") == "control"
    assert resolver.plane_for("tool") == "generation"


def test_unknown_type_falls_back_to_undetermined(
    resolver: CanonicalTypePlaneResolver,
) -> None:
    """Given a canonical type absent from the type -> node map,
    When the plane is resolved,
    Then it is `undetermined` rather than a guessed plane.

    Manual mappings carry a free-text `component_kind`, so an unlisted
    type is expected traffic; surfacing it in the undetermined band is
    the visible-not-misplaced contract.
    """
    # Given / When / Then
    assert resolver.plane_for("manual_mapping") == UNDETERMINED_PLANE
    assert resolver.plane_for("totally_unknown_kind") == "undetermined"


def test_every_bridge_component_kind_resolves_to_a_real_plane(
    resolver: CanonicalTypePlaneResolver,
) -> None:
    """Task 0 coverage audit: no bridge-emitted component may land in
    the undetermined band because its canonical_type is missing from
    `capability_type_node_map.toml`.
    """
    # Given
    kinds = _bridge_component_kinds()

    # When
    undetermined = tuple(
        kind
        for kind in kinds
        if resolver.plane_for(kind) == UNDETERMINED_PLANE
    )

    # Then
    assert undetermined == ()


def test_resolver_rejects_a_catalog_plane_outside_the_canonical_layers(
    catalog: CapabilityReferenceCatalog,
) -> None:
    """Given a catalog whose node names a plane the canonical model has
    no `layer` value for,
    When the resolver is built,
    Then it fails closed instead of emitting an off-contract layer.
    """
    # Given
    off_contract = catalog.nodes[0].model_copy(
        update={"plane_id": "not_a_plane"}
    )
    broken = catalog.model_copy(
        update={"nodes": (off_contract, *catalog.nodes[1:])}
    )

    # When / Then
    with pytest.raises(
        CanonicalTypePlaneError,
        match="not a canonical layer",
    ):
        CanonicalTypePlaneResolver(catalog=broken)
