"""Load the packaged canonical type -> reference node mapping.

Responsibility: read `capability_type_node_map.toml` -- the single
source of truth for the Step 6 assessment lookup -- and fail-closed
validate that every node id exists in the 52-node capability
reference catalog.
Call chain: ReferenceCapabilityAssessmentService.__init__ -> load().
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from importlib import resources
from typing import Any

from kai_mind.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)

RULES_PACKAGE = "kai_mind.core.rules"
MAP_RESOURCE = "capability_type_node_map.toml"
MAP_SECTION = "canonical_type_nodes"


class CapabilityTypeNodeMapError(ValueError):
    """Raised when the packaged type -> node mapping is malformed."""


class CapabilityTypeNodeMapLoader:
    """Load and fail-closed validate the canonical type -> node map."""

    def load(
        self,
        catalog: CapabilityReferenceCatalog,
    ) -> Mapping[str, tuple[str, ...]]:
        try:
            text = (
                resources.files(RULES_PACKAGE)
                .joinpath(MAP_RESOURCE)
                .read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise CapabilityTypeNodeMapError(
                f"failed to read packaged {MAP_RESOURCE}: {exc}"
            ) from exc
        return self.parse_text(text, catalog)

    def parse_text(
        self,
        text: str,
        catalog: CapabilityReferenceCatalog,
    ) -> Mapping[str, tuple[str, ...]]:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise CapabilityTypeNodeMapError(
                f"failed to parse {MAP_RESOURCE}: {exc}"
            ) from exc
        unknown_sections = set(payload) - {MAP_SECTION}
        if unknown_sections:
            joined = ", ".join(sorted(unknown_sections))
            raise CapabilityTypeNodeMapError(
                f"{MAP_RESOURCE}: unknown section: {joined}"
            )
        entries: Any = payload.get(MAP_SECTION, {})
        if not isinstance(entries, Mapping) or not entries:
            raise CapabilityTypeNodeMapError(
                f"{MAP_RESOURCE}: [{MAP_SECTION}] must be a non-empty table"
            )
        known_node_ids = {node.id for node in catalog.nodes}
        return {
            canonical_type: self._node_ids(
                canonical_type,
                value,
                known_node_ids,
            )
            for canonical_type, value in entries.items()
        }

    def _node_ids(
        self,
        canonical_type: str,
        value: Any,
        known_node_ids: set[str],
    ) -> tuple[str, ...]:
        if (
            not isinstance(value, list)
            or not value
            or any(
                not isinstance(item, str) or not item.strip() for item in value
            )
        ):
            raise CapabilityTypeNodeMapError(
                f"{MAP_RESOURCE}: [{MAP_SECTION}].{canonical_type} must be "
                f"a non-empty list of node ids, got {value!r}"
            )
        unknown = tuple(item for item in value if item not in known_node_ids)
        if unknown:
            raise CapabilityTypeNodeMapError(
                f"{MAP_RESOURCE}: [{MAP_SECTION}].{canonical_type} "
                f"references unknown reference node id '{unknown[0]}'; "
                "every node id must exist in the 52-node capability "
                "reference catalog"
            )
        return tuple(value)
