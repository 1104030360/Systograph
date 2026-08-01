from __future__ import annotations

from collections.abc import Mapping

from systograph.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from systograph.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from systograph.core.services.capability_type_node_map_loader import (
    CapabilityTypeNodeMapLoader,
)
from systograph.core.services.component_bridge_rules import (
    COMPONENT_BRIDGE_RULES,
)
from systograph.core.services.reference_capability_assessment_service import (
    ReferenceCapabilityAssessmentService,
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


def test_packaged_map_survives_fail_closed_load_against_catalog() -> None:
    """Loading is the subset check -- there is no assertion to make.

    CapabilityTypeNodeMapLoader validates every node id against the
    52-node catalog and raises CapabilityTypeNodeMapError on the first
    unknown one, so a "values are inside the catalog" assertion here
    could never fail: load() would raise before the assert ran. The
    live invariant is that the packaged mapping still passes that
    fail-closed validation against the real catalog, which is exactly
    what ReferenceCapabilityAssessmentService does when it is
    constructed -- a broken map is a startup crash, not a wrong score.
    Key/value drift is pinned separately in
    tests/unit/core/test_capability_type_node_map_loader.py.
    """
    # Given
    catalog = _catalog()

    # When: constructing the consumer re-runs the same fail-closed load,
    # so this line raises if the packaged map ever drifts out of the
    # catalog.
    ReferenceCapabilityAssessmentService(catalog=catalog)
    mapping = CapabilityTypeNodeMapLoader().load(catalog)

    # Then
    assert mapping
