"""Derive a component's projection plane from its canonical type.

Responsibility: answer `canonical_type -> primary capability node ->
node.plane_id` for the active v2 path, so a component is painted onto
the plane its capability belongs to instead of the plane its legacy
`rag-core-v1` slot happened to name.

Composition: both halves of the chain already exist and are reused
verbatim -- `CapabilityTypeNodeMapLoader` supplies the fail-closed
`canonical_type -> node ids` map, `CapabilityReferenceMapLoader`
supplies the 52-node catalog with each node's `plane_id`. This module
only joins them; it owns no mapping table of its own.

Primary-node convention: a canonical type may reach several nodes
(`api_input = ["user_input", "api_server"]`). The FIRST node in the
TOML array is the primary and decides the plane -- the same convention
documented in `capability_type_node_map.toml`.

Call chain:
  SystemMapV2NormalizeService._components()
    -> CanonicalTypePlaneResolver.plane_for(instance.kind)
"""

from __future__ import annotations

from typing import Final, cast, get_args

from systograph.core.models.ai_system_map_v2 import CanonicalLayer
from systograph.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from systograph.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from systograph.core.services.capability_type_node_map_loader import (
    CapabilityTypeNodeMapLoader,
)

UNDETERMINED_PLANE: Final[CanonicalLayer] = "undetermined"
CANONICAL_LAYERS: Final[frozenset[str]] = frozenset(get_args(CanonicalLayer))


class CanonicalTypePlaneError(ValueError):
    """Raised when the catalog names a plane the canonical model lacks."""


class CanonicalTypePlaneResolver:
    """Resolve a canonical component type to its projection plane."""

    def __init__(
        self,
        *,
        catalog: CapabilityReferenceCatalog | None = None,
    ) -> None:
        resolved = catalog or CapabilityReferenceMapLoader().load()
        plane_by_node = {
            node.id: self._canonical_layer(node.id, node.plane_id)
            for node in resolved.nodes
        }
        type_to_nodes = CapabilityTypeNodeMapLoader().load(resolved)
        self._plane_by_type: dict[str, CanonicalLayer] = {
            canonical_type: plane_by_node[node_ids[0]]
            for canonical_type, node_ids in type_to_nodes.items()
        }

    def plane_for(self, canonical_type: str) -> CanonicalLayer:
        """Plane for `canonical_type`; `undetermined` when unlisted.

        An unlisted type is expected traffic -- manual mappings carry a
        free-text `component_kind` -- so it surfaces in the undetermined
        band rather than borrowing a plane from anywhere else.
        """
        return self._plane_by_type.get(canonical_type, UNDETERMINED_PLANE)

    @staticmethod
    def _canonical_layer(node_id: str, plane_id: str) -> CanonicalLayer:
        if plane_id not in CANONICAL_LAYERS:
            raise CanonicalTypePlaneError(
                f"capability node '{node_id}' names plane '{plane_id}', "
                "which is not a canonical layer"
            )
        return cast(CanonicalLayer, plane_id)
