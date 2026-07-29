from __future__ import annotations

from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from kai_mind.core.services.component_bridge_rules import (
    COMPONENT_BRIDGE_RULES,
)
from kai_mind.core.services.reference_capability_assessment_service import (
    _TYPE_TO_NODES,
)


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

    # When
    unreachable = tuple(kind for kind in kinds if not _TYPE_TO_NODES.get(kind))

    # Then
    assert unreachable == ()


def test_reference_node_vocabulary_stays_inside_catalog() -> None:
    # Given
    catalog_node_ids = {
        node.id for node in CapabilityReferenceMapLoader().load().nodes
    }

    # When
    unknown = {
        node_id
        for node_ids in _TYPE_TO_NODES.values()
        for node_id in node_ids
        if node_id not in catalog_node_ids
    }

    # Then
    assert unknown == set()
