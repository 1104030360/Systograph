"""Dual-read loader for ai-system-map/v1 and ai-system-map/v2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.services.system_map_v1_to_v2_adapter import (
    LegacySystemMapAdaptError,
    SystemMapV1ToV2Adapter,
)
from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationError,
    SystemMapV2ValidationService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationError,
    SystemMapValidationService,
)

ActiveSchemaVersion = Literal["ai-system-map/v1", "ai-system-map/v2"]


class CanonicalMapLoadError(ValueError):
    """Raised when dual-read loading fails."""


@dataclass(frozen=True, slots=True)
class CanonicalMapLoadResult:
    active_schema_version: ActiveSchemaVersion
    normalized: AiSystemMapV2
    migration_warnings: list[str]


class CanonicalMapLoader:
    """Own all schema branching for map payloads.

    Routes and downstream services must consume the normalized v2 view from
    this loader instead of inspecting schema_version themselves.
    """

    def __init__(
        self,
        *,
        v1_validation_service: SystemMapValidationService | None = None,
        v2_validation_service: SystemMapV2ValidationService | None = None,
        adapter: SystemMapV1ToV2Adapter | None = None,
    ) -> None:
        self._v1_validation_service = (
            v1_validation_service or SystemMapValidationService()
        )
        self._v2_validation_service = (
            v2_validation_service or SystemMapV2ValidationService()
        )
        self._adapter = adapter or SystemMapV1ToV2Adapter()

    def load(self, data: Mapping[str, Any]) -> CanonicalMapLoadResult:
        schema_version = data.get("schema_version")
        if schema_version == "ai-system-map/v1":
            return self._load_v1(data)
        if schema_version == "ai-system-map/v2":
            return self._load_v2(data)
        raise CanonicalMapLoadError(
            f"unsupported schema_version: {schema_version!r}"
        )

    def _load_v1(self, data: Mapping[str, Any]) -> CanonicalMapLoadResult:
        try:
            system_map = self._v1_validation_service.validate(data)
            normalized = self._adapter.adapt_to_canonical(system_map)
            self._v2_validation_service.validate(
                normalized.model_dump(mode="json")
            )
        except (
            SystemMapValidationError,
            LegacySystemMapAdaptError,
            SystemMapV2ValidationError,
        ) as exc:
            raise CanonicalMapLoadError(str(exc)) from exc
        return CanonicalMapLoadResult(
            active_schema_version="ai-system-map/v1",
            normalized=normalized,
            migration_warnings=list(normalized.migration_warnings),
        )

    def _load_v2(self, data: Mapping[str, Any]) -> CanonicalMapLoadResult:
        try:
            normalized = self._v2_validation_service.validate(data)
        except SystemMapV2ValidationError as exc:
            raise CanonicalMapLoadError(str(exc)) from exc
        return CanonicalMapLoadResult(
            active_schema_version="ai-system-map/v2",
            normalized=normalized,
            migration_warnings=list(normalized.migration_warnings),
        )
