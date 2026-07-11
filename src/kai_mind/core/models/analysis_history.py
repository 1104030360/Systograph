from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kai_mind.core.models.scan import ProjectScanResult

BuildReason = Literal[
    "initial_scan",
    "apply_confirmations",
    "detail_scan",
]


class AnalysisHistoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScanSnapshot(AnalysisHistoryModel):
    schema_version: Literal["scan-snapshot/v1"] = "scan-snapshot/v1"
    project_id: str
    scan_id: str
    generated_at: datetime
    inventory_digest: str
    scan_result: ProjectScanResult
    file_fingerprints: dict[str, str] = Field(default_factory=dict)
    ua_analysis_result: dict[str, Any] | None = None


class ScanSnapshotManifest(AnalysisHistoryModel):
    schema_version: Literal["scan-snapshot-manifest/v1"] = (
        "scan-snapshot-manifest/v1"
    )
    project_id: str
    scan_id: str
    generated_at: datetime
    inventory_digest: str
    ua_analysis_available: bool = False


class MapBuildLineage(AnalysisHistoryModel):
    project_id: str
    scan_id: str
    build_id: str
    based_on_build_id: str | None = None
    build_reason: BuildReason
    applied_mapping_ids: tuple[str, ...] = ()
    generated_at: datetime

    @model_validator(mode="after")
    def validate_lineage(self) -> MapBuildLineage:
        if len(self.applied_mapping_ids) != len(set(self.applied_mapping_ids)):
            raise ValueError("applied_mapping_ids must be unique")
        if self.build_reason == "initial_scan":
            if self.based_on_build_id is not None or self.applied_mapping_ids:
                raise ValueError(
                    "initial build cannot have parent or mappings"
                )
        elif self.build_reason == "apply_confirmations":
            if self.based_on_build_id is None or not self.applied_mapping_ids:
                raise ValueError("apply build requires parent and mappings")
        elif self.based_on_build_id is None:
            raise ValueError("detail build requires parent")
        return self


class LatestBuildPointer(AnalysisHistoryModel):
    project_id: str
    latest_build_id: str
    revision: int = Field(ge=1)
    updated_at: datetime


class ProjectState(AnalysisHistoryModel):
    schema_version: Literal["project-state/v1"] = "project-state/v1"
    project_id: str
    project_name: str
    source_type: Literal["local_path"]
    canonical_path: str
    path_digest: str
    created_at: datetime
    active: bool = True


class MapBuildManifest(AnalysisHistoryModel):
    schema_version: Literal["map-build-manifest/v1"] = "map-build-manifest/v1"
    lineage: MapBuildLineage
    output_dir: str
    artifact_digests: dict[str, str]
    active_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"] = (
        "ai-system-map/v1"
    )
    requested_schema_version: Literal[
        "ai-system-map/v1", "ai-system-map/v2"
    ] = "ai-system-map/v1"
    migration_warnings: tuple[str, ...] = ()
    apply_request_digest: str | None = None
    status: Literal["complete"] = "complete"
