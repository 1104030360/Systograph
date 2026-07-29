from __future__ import annotations

from collections.abc import Mapping

from kai_mind.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from kai_mind.core.services.capability_type_node_map_loader import (
    CapabilityTypeNodeMapLoader,
)
from kai_mind.core.services.component_bridge_rules import (
    COMPONENT_BRIDGE_RULES,
)


def _catalog() -> CapabilityReferenceCatalog:
    return CapabilityReferenceMapLoader().load()


def _type_to_nodes(
    catalog: CapabilityReferenceCatalog,
) -> Mapping[str, tuple[str, ...]]:
    """The packaged canonical_type -> reference node lookup."""
    return CapabilityTypeNodeMapLoader().load(catalog)


def _bridge_component_kinds() -> tuple[str, ...]:
    """Distinct canonical_type values the bridge rules can emit."""
    return tuple(
        dict.fromkeys(
            spec.kind
            for rule in COMPONENT_BRIDGE_RULES
            for spec in rule.candidates
        )
    )


def test_every_bridge_component_kind_reaches_a_reference_node() -> None:
    # Given
    kinds = _bridge_component_kinds()
    type_to_nodes = _type_to_nodes(_catalog())

    # When
    unreachable = tuple(kind for kind in kinds if not type_to_nodes.get(kind))

    # Then
    assert unreachable == ()


def test_reference_node_vocabulary_stays_inside_catalog() -> None:
    # Given
    catalog = _catalog()
    catalog_node_ids = {node.id for node in catalog.nodes}

    # When
    unknown = {
        node_id
        for node_ids in _type_to_nodes(catalog).values()
        for node_id in node_ids
        if node_id not in catalog_node_ids
    }

    # Then
    assert unknown == set()
