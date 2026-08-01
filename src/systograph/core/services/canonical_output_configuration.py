from __future__ import annotations

import os
from typing import Final, cast

from systograph.core.models.map_build import SystemMapSchemaSelection

CANONICAL_OUTPUT_ENV = "SYSTOGRAPH_CANONICAL_OUTPUT_VERSION"
# Operator rollback selection. Callers compare against this constant so the
# legacy literal stays owned by this module instead of spreading into the
# active build path.
LEGACY_CANONICAL_OUTPUT_VERSION: Final[SystemMapSchemaSelection] = (
    "ai-system-map/v1"
)


class CanonicalOutputConfigurationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


def canonical_output_version_from_env() -> SystemMapSchemaSelection:
    value = os.environ.get(CANONICAL_OUTPUT_ENV, "ai-system-map/v2")
    if value not in {"ai-system-map/v1", "ai-system-map/v2"}:
        raise CanonicalOutputConfigurationError(
            "invalid_canonical_output_version"
        )
    return cast(SystemMapSchemaSelection, value)


def require_public_v2_selection(
    requested: SystemMapSchemaSelection,
) -> None:
    if requested == LEGACY_CANONICAL_OUTPUT_VERSION:
        raise CanonicalOutputConfigurationError("legacy_output_not_selectable")
