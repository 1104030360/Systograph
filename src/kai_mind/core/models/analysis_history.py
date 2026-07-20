from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kai_mind.core.models.artifact_scope import (
    PHASE2_P0_ARTIFACT_SET_VERSION,
    ArtifactSetVersion,
)
from kai_mind.core.models.inventory_selection import InventorySelectionSummary
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
    inventory_provenance_status: Literal[
        "recorded",
        "legacy_inventory_policy_unknown",
    ] = "legacy_inventory_policy_unknown"
    inventory_policy_schema_version: str | None = None
    inventory_policy_digest: str | None = None
    candidate_set_digest: str | None = None
    filesystem_safety_version: str | None = None
    boundary_decision_digest: str | None = None
    final_inventory_digest: str | None = None
    inventory_run_digest: str | None = None
    inventory_source_mode: (
        Literal[
            "git",
            "recursive",
            "fallback_after_git_error",
        ]
        | None
    ) = None
    file_fingerprints: dict[str, str] = Field(default_factory=dict)
    inventory_selection_summary: InventorySelectionSummary | None = None
    ua_analysis_result: dict[str, Any] | None = None


class ScanSnapshotManifest(AnalysisHistoryModel):
    schema_version: Literal["scan-snapshot-manifest/v1"] = (
        "scan-snapshot-manifest/v1"
    )
    project_id: str
    scan_id: str
    generated_at: datetime
    inventory_digest: str
    inventory_provenance_status: Literal[
        "recorded",
        "legacy_inventory_policy_unknown",
    ] = "legacy_inventory_policy_unknown"
    inventory_policy_schema_version: str | None = None
    inventory_policy_digest: str | None = None
    candidate_set_digest: str | None = None
    filesystem_safety_version: str | None = None
    boundary_decision_digest: str | None = None
    final_inventory_digest: str | None = None
    inventory_run_digest: str | None = None
    inventory_source_mode: (
        Literal[
            "git",
            "recursive",
            "fallback_after_git_error",
        ]
        | None
    ) = None
    inventory_selection_summary: InventorySelectionSummary | None = None
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


class ArtifactManifestEntry(AnalysisHistoryModel):
    digest: str
    size_bytes: int = Field(gt=0)
    schema_status: Literal["validated"] = "validated"
    schema_version: str | None = None


class MapBuildManifest(AnalysisHistoryModel):
    schema_version: Literal["map-build-manifest/v1"] = "map-build-manifest/v1"
    lineage: MapBuildLineage
    output_dir: str
    artifact_set_version: ArtifactSetVersion = PHASE2_P0_ARTIFACT_SET_VERSION
    environment_id: str = "environment:default-static"
    artifact_digests: dict[str, str]
    artifacts: dict[str, ArtifactManifestEntry] = Field(default_factory=dict)
    active_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"] = (
        "ai-system-map/v1"
    )
    requested_schema_version: Literal[
        "ai-system-map/v1", "ai-system-map/v2"
    ] = "ai-system-map/v1"
    source_schema_version: (
        Literal["ai-system-map/v1", "ai-system-map/v2"] | None
    ) = None
    operator_rollback_active: bool = False
    migration_warnings: tuple[str, ...] = ()
    apply_request_digest: str | None = None
    status: Literal["complete"] = "complete"
