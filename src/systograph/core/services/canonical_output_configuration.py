from __future__ import annotations

import os
from typing import Final, cast

from systograph.core.models.map_build import SystemMapSchemaSelection

CANONICAL_OUTPUT_ENV = "SYSTOGRAPH_CANONICAL_OUTPUT_VERSION"
# The legacy public selection. Nothing writes v1 any more; the constant
# survives so require_public_v2_selection() can keep answering an API/CLI
# request for v1 with the stable legacy_output_not_selectable code instead
# of a generic pydantic 422. The literal stays owned by this module rather
# than spreading into the active build path.
LEGACY_CANONICAL_OUTPUT_VERSION: Final[SystemMapSchemaSelection] = (
    "ai-system-map/v1"
)


class CanonicalOutputConfigurationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


# v2 is the only version this process can produce. The legacy value is not
# special-cased: with the rollback writer gone it is simply unsupported, so
# it fails with the same stable code as any other unknown value.
def canonical_output_version_from_env() -> SystemMapSchemaSelection:
    value = os.environ.get(CANONICAL_OUTPUT_ENV, "ai-system-map/v2")
    if value != "ai-system-map/v2":
        raise CanonicalOutputConfigurationError(
            "invalid_canonical_output_version"
        )
    return cast(SystemMapSchemaSelection, value)


def require_public_v2_selection(
    requested: SystemMapSchemaSelection,
) -> None:
    if requested == LEGACY_CANONICAL_OUTPUT_VERSION:
        raise CanonicalOutputConfigurationError("legacy_output_not_selectable")
