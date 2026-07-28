from __future__ import annotations

import tomllib
from importlib import resources

from pydantic import ValidationError

from systograph.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)

RULES_PACKAGE = "systograph.core.rules"
CATALOG_RESOURCE = "capability_reference_map.toml"
EXPECTED_CATALOG_ID = "ai-system-capability-reference-map"
EXPECTED_VERSION = "1"
EXPECTED_PLANE_COUNT = 10
EXPECTED_NODE_COUNT = 52


class CapabilityReferenceMapError(ValueError):
    pass


class CapabilityReferenceMapLoader:
    def load(self) -> CapabilityReferenceCatalog:
        try:
            text = (
                resources.files(RULES_PACKAGE)
                .joinpath(CATALOG_RESOURCE)
                .read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise CapabilityReferenceMapError(
                f"failed to read packaged capability catalog: {exc}"
            ) from exc
        return self._validate_active_catalog(self.parse_text(text))

    def parse_text(self, text: str) -> CapabilityReferenceCatalog:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise CapabilityReferenceMapError(
                f"failed to parse capability catalog: {exc}"
            ) from exc
        try:
            return CapabilityReferenceCatalog.model_validate(payload)
        except ValidationError as exc:
            raise CapabilityReferenceMapError(str(exc)) from exc

    def _validate_active_catalog(
        self,
        catalog: CapabilityReferenceCatalog,
    ) -> CapabilityReferenceCatalog:
        if catalog.catalog_id != EXPECTED_CATALOG_ID:
            raise CapabilityReferenceMapError("unexpected catalog_id")
        if catalog.version != EXPECTED_VERSION:
            raise CapabilityReferenceMapError("unexpected catalog version")
        if len(catalog.planes) != EXPECTED_PLANE_COUNT:
            raise CapabilityReferenceMapError("catalog must contain 10 planes")
        if len(catalog.nodes) != EXPECTED_NODE_COUNT:
            raise CapabilityReferenceMapError("catalog must contain 52 nodes")
        return catalog
