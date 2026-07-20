from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.mapping import ManualMapping
from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.system_map_materialization_service import (
    SystemMapMaterializationService,
)


@dataclass(frozen=True, slots=True)
class LegacyV1RollbackError(ValueError):
    code: str

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class LegacyV1RollbackResult:
    artifact_map: RagSystemMap
    normalized_map: AiSystemMapV2
    detection: ComponentDetectionResult
    manual_mappings: tuple[ManualMapping, ...]


class LegacyV1RollbackService:
    def __init__(
        self,
        *,
        materialization_service: SystemMapMaterializationService,
        canonical_map_loader: CanonicalMapLoader | None = None,
    ) -> None:
        self._materialization = materialization_service
        self._loader = canonical_map_loader or CanonicalMapLoader()

    def materialize(
        self,
        *,
        raw_scan: ProjectScanResult,
        project_name: str,
        project_root: Path,
        request: MapBuildRequest,
        project_id: str | None,
        mapping_ids: tuple[str, ...] | None,
    ) -> LegacyV1RollbackResult:
        materialized = self._materialization.materialize(
            raw_scan=raw_scan,
            project_name=project_name,
            project_root=project_root,
            request=request,
            project_id=project_id,
            mapping_ids=mapping_ids,
        )
        loaded = self._loader.load(
            materialized.system_map.model_dump(mode="json")
        )
        normalized = loaded.normalized.model_copy(
            update={
                "migration_warnings": [
                    *loaded.migration_warnings,
                    "operator_rollback_active",
                ]
            }
        )
        return LegacyV1RollbackResult(
            artifact_map=materialized.system_map,
            normalized_map=normalized,
            detection=materialized.detection,
            manual_mappings=materialized.manual_mappings,
        )

    @staticmethod
    def require_representable(system_map: AiSystemMapV2) -> None:
        if system_map.source_schema_version != "ai-system-map/v1":
            raise LegacyV1RollbackError("legacy_rollback_not_representable")
        if any(
            component.metadata.get("semantic_kind")
            not in {"repo_component", "slot_placeholder", "legacy_extension"}
            for component in system_map.components
        ):
            raise LegacyV1RollbackError("legacy_rollback_not_representable")
