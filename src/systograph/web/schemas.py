"""Pydantic request and response schemas for the local web API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.analysis_history import MapBuildManifest
from systograph.core.models.apply_confirmations import ApplyConfirmationsResult
from systograph.core.models.inventory_selection import (
    InventoryDirectoryLimitContext,
    InventoryPreflightRequest,
    InventoryPreflightSummary,
    InventoryRequestedTargetStatus,
    InventorySelectionSummary,
    InventoryTargetKind,
)
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingUpdate,
    MappingProposal,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
    MappingProposalDecisionResult,
)
from systograph.core.models.profile_signal import ProfileInferenceResult
from systograph.core.models.readiness_report import ReadinessReport
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryProposal,
)
from systograph.core.models.system_map import DetailScanResult
from systograph.core.models.viewer import ViewerLoadResult, ViewerPayload


class WebSchema(BaseModel):
    """Base schema that rejects silent API contract drift."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MapBuildApiRequest(WebSchema):
    project_path: str
    output: str = "outputs"
    redact_root_path: bool = True
    no_snippets: bool = False
    system_map_schema_version: Literal[
        "ai-system-map/v1",
        "ai-system-map/v2",
    ] = "ai-system-map/v2"

    def to_core_request(self) -> MapBuildRequest:
        return MapBuildRequest(
            project_path=Path(self.project_path),
            output=Path(self.output),
            redact_root_path=self.redact_root_path,
            no_snippets=self.no_snippets,
            system_map_schema_version=self.system_map_schema_version,
        )


class ProjectImportRequest(WebSchema):
    source_type: Literal["local_path"]
    project_path: str


class ProjectImportResponse(WebSchema):
    project_id: str
    source_type: Literal["local_path"]
    project_name: str
    project_path: str
    reused: bool = False


class ProjectResponse(WebSchema):
    project_id: str
    source_type: Literal["local_path"]
    project_name: str


class Phase2MapBuildResult(WebSchema):
    status: Literal["ok", "error"]
    project_name: str
    active_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"]
    requested_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"]
    source_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"]
    operator_rollback_active: bool
    migration_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    profile_signals_available: bool
    readiness_report_available: bool
    profile_inference_result: ProfileInferenceResult | None
    readiness_report: ReadinessReport | None

    @classmethod
    def from_core(cls, result: MapBuildResult) -> Phase2MapBuildResult:
        return cls(
            status=result.status,
            project_name=result.project_name,
            active_schema_version=result.active_schema_version,
            requested_schema_version=result.requested_schema_version,
            source_schema_version=result.source_schema_version,
            operator_rollback_active=result.operator_rollback_active,
            migration_warnings=result.migration_warnings,
            warnings=result.warnings,
            profile_signals_available=(
                result.profile_inference_result is not None
            ),
            readiness_report_available=result.readiness_report is not None,
            profile_inference_result=result.profile_inference_result,
            readiness_report=result.readiness_report,
        )


class ApplyConfirmationsRequest(WebSchema):
    mapping_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> ApplyConfirmationsRequest:
        if len(self.mapping_ids) != len(set(self.mapping_ids)):
            raise ValueError("mapping_ids must be unique")
        return self


class MapBuildScopedResponse(WebSchema):
    project_id: str
    scan_id: str
    build_id: str
    based_on_build_id: str | None
    build_reason: Literal["initial_scan", "apply_confirmations", "detail_scan"]
    applied_mapping_ids: list[str]
    build_result: Phase2MapBuildResult
    viewer_load_result: ViewerLoadResult

    @classmethod
    def from_core(cls, result: MapBuildResult) -> MapBuildScopedResponse:
        lineage = result.lineage
        viewer = result.viewer_load_result
        if lineage is None or viewer is None:
            raise ValueError(
                "build response requires lineage and viewer result"
            )
        return cls(
            project_id=lineage.project_id,
            scan_id=lineage.scan_id,
            build_id=lineage.build_id,
            based_on_build_id=lineage.based_on_build_id,
            build_reason=lineage.build_reason,
            applied_mapping_ids=list(lineage.applied_mapping_ids),
            build_result=Phase2MapBuildResult.from_core(result),
            viewer_load_result=viewer,
        )


class ApplyConfirmationsResponse(MapBuildScopedResponse):
    build_reason: Literal["apply_confirmations"]
    based_on_build_id: str

    @classmethod
    def from_domain(
        cls,
        result: ApplyConfirmationsResult,
    ) -> ApplyConfirmationsResponse:
        return cls(
            project_id=result.project_id,
            scan_id=result.scan_id,
            build_id=result.build_id,
            based_on_build_id=result.based_on_build_id,
            build_reason="apply_confirmations",
            applied_mapping_ids=list(result.applied_mapping_ids),
            build_result=Phase2MapBuildResult.from_core(result.build_result),
            viewer_load_result=result.viewer_load_result,
        )


class MapBuildHistorySummary(WebSchema):
    project_id: str
    scan_id: str
    build_id: str
    based_on_build_id: str | None
    build_reason: Literal["initial_scan", "apply_confirmations", "detail_scan"]
    applied_mapping_ids: list[str]
    generated_at: str

    @classmethod
    def from_manifest(
        cls,
        manifest: MapBuildManifest,
    ) -> MapBuildHistorySummary:
        lineage = manifest.lineage
        return cls(
            project_id=lineage.project_id,
            scan_id=lineage.scan_id,
            build_id=lineage.build_id,
            based_on_build_id=lineage.based_on_build_id,
            build_reason=lineage.build_reason,
            applied_mapping_ids=list(lineage.applied_mapping_ids),
            generated_at=lineage.generated_at.isoformat().replace(
                "+00:00", "Z"
            ),
        )


class MapBuildHistoryResponse(WebSchema):
    project_id: str
    builds: list[MapBuildHistorySummary]


class ScanCreateRequest(WebSchema):
    project_id: str
    scan_depth: Literal["system"] = "system"
    output: str = "outputs"
    redact_root_path: bool = True
    no_snippets: bool = False
    system_map_schema_version: Literal[
        "ai-system-map/v1",
        "ai-system-map/v2",
    ] = "ai-system-map/v2"
    boundary_decisions: list[ScanBoundaryDecisionRequest] = Field(
        default_factory=list
    )
    preflight_request_id: str | None = None


class ScanCreateResponse(WebSchema):
    scan_id: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    project_id: str
    status: Literal["completed", "error", "requires_boundary_decision"]
    build_result: MapBuildResult | None = None
    boundary_proposals: list[ScanBoundaryProposal] = Field(
        default_factory=list
    )
    available_boundary_actions: list[ScanBoundaryDecisionAction] = Field(
        default_factory=lambda: [
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
        ]
    )
    preflight_request_id: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    inventory_selection_summary: InventorySelectionSummary | None = None


class InventoryPreflightApiRequest(WebSchema):
    scan_depth: Literal["system"] = "system"
    requested_paths: tuple[str, ...] = ()
    reviewable_excluded_cursor: str | None = None
    reviewable_excluded_limit: int = Field(default=100, ge=1, le=200)

    def to_core(self) -> InventoryPreflightRequest:
        return InventoryPreflightRequest.model_validate(
            self.model_dump(mode="python")
        )


class InventoryRequestedTargetView(WebSchema):
    target_path: str
    target_kind: InventoryTargetKind
    status: InventoryRequestedTargetStatus
    proposal: ScanBoundaryProposal | None = None
    reason_code: str | None = None
    limit_context: InventoryDirectoryLimitContext | None = None


class InventoryReviewableExcludedPageView(WebSchema):
    items: list[ScanBoundaryProposal] = Field(default_factory=list)
    next_cursor: str | None = None
    total: int


class InventoryBlockedSummaryView(WebSchema):
    path: str
    reason_code: str
    outcome: Literal["hard_blocked", "collapsed_directory"]
    can_expand: bool = False


class InventoryPreflightResponse(WebSchema):
    preflight_request_id: str
    project_id: str
    generated_at: str
    source_mode: Literal[
        "git",
        "recursive",
        "fallback_after_git_error",
    ]
    inventory_policy_schema_version: str
    inventory_policy_digest: str
    candidate_set_digest: str
    filesystem_safety_version: str
    summary: InventoryPreflightSummary
    required_boundary_proposals: list[ScanBoundaryProposal] = Field(
        default_factory=list
    )
    reviewable_excluded_page: InventoryReviewableExcludedPageView
    requested_target_results: list[InventoryRequestedTargetView] = Field(
        default_factory=list
    )
    blocked_summaries: list[InventoryBlockedSummaryView] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)


class InventoryApiErrorDetail(WebSchema):
    code: str
    message: str
    retryable: bool = False
    context: dict[str, str | int] | None = None


class ScanProgressEvent(WebSchema):
    event: str = "scan_progress"
    status: Literal["running", "completed", "error"] = "completed"
    stage: str = "validate"
    message: str = "Scan completed."
    percent: int = Field(default=100, ge=0, le=100)
    node_id: str | None = None
    edge_id: str | None = None
    component_id: str | None = None
    source_id: str | None = None
    slot: str | None = None
    evidence_id: str | None = None
    scan_depth: str = "system"
    timestamp: str = Field(
        default_factory=lambda: (
            datetime.now(UTC).isoformat().replace("+00:00", "Z")
        )
    )


class DetailScanCreateRequest(WebSchema):
    project_id: str
    build_id: str | None = None
    target_type: str
    target: str
    scan_depth: Literal["component", "code_path"] = "component"


class DetailScanResponse(WebSchema):
    project_id: str
    detail_scan: DetailScanResult
    ai_system_map: AiSystemMapV2
    source_build_id: str | None = None
    build_id: str | None = None
    scan_id: str | None = None
    viewer_load_result: ViewerLoadResult | None = None
    warnings: list[str] = Field(default_factory=list)


class TraceCreateRequest(WebSchema):
    project_id: str
    build_id: str | None = None
    endpoint_id: str
    query: str
    timeout_seconds: float = Field(default=30.0, gt=0, le=120)


class ManualMappingListResponse(WebSchema):
    project_id: str
    mappings: list[ManualMapping]
    available_actions: list[str] = Field(
        default_factory=lambda: [
            "confirm",
            "edit",
            "reject",
            "skip_for_now",
            "mark_not_applicable",
        ]
    )


class MappingProposalCreateRequest(WebSchema):
    project_id: str
    source_unmapped_id: str
    user_description: str | None = None


class MappingProposalListResponse(WebSchema):
    project_id: str
    proposals: list[MappingProposal]
    available_actions: list[MappingProposalDecisionAction] = Field(
        default_factory=lambda: [
            MappingProposalDecisionAction.ACCEPT,
            MappingProposalDecisionAction.EDIT,
            MappingProposalDecisionAction.REJECT,
            MappingProposalDecisionAction.SKIP_FOR_NOW,
        ]
    )


__all__ = [
    "DetailScanCreateRequest",
    "DetailScanResponse",
    "MapBuildApiRequest",
    "MapBuildResult",
    "ManualMapping",
    "ManualMappingCreate",
    "ManualMappingListResponse",
    "ManualMappingUpdate",
    "MappingProposal",
    "MappingProposalCreateRequest",
    "MappingProposalDecisionRequest",
    "MappingProposalDecisionResult",
    "MappingProposalListResponse",
    "ProjectImportRequest",
    "ProjectImportResponse",
    "ScanBoundaryDecisionRequest",
    "ScanBoundaryProposal",
    "ScanCreateRequest",
    "ScanCreateResponse",
    "ScanProgressEvent",
    "TraceCreateRequest",
    "ViewerPayload",
]
