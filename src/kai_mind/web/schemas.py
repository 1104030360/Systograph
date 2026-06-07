"""Pydantic request and response schemas for the local web API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingUpdate,
)
from kai_mind.core.models.viewer import ViewerPayload


class WebSchema(BaseModel):
    """Base schema that rejects silent API contract drift."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MapBuildApiRequest(WebSchema):
    project_path: str
    output: str = "outputs"
    redact_root_path: bool = True
    no_snippets: bool = False

    def to_core_request(self) -> MapBuildRequest:
        return MapBuildRequest(
            project_path=Path(self.project_path),
            output=Path(self.output),
            redact_root_path=self.redact_root_path,
            no_snippets=self.no_snippets,
        )


class ViewerLoadMapRequest(WebSchema):
    map_json_path: str


class ProjectImportRequest(WebSchema):
    source_type: Literal["local_path"]
    project_path: str


class ProjectImportResponse(WebSchema):
    project_id: str
    source_type: Literal["local_path"]
    project_name: str
    project_path: str


class ScanCreateRequest(WebSchema):
    project_id: str
    scan_depth: Literal["system"] = "system"
    output: str = "outputs"
    redact_root_path: bool = True
    no_snippets: bool = False


class ScanCreateResponse(WebSchema):
    scan_id: str
    project_id: str
    status: Literal["completed", "error"]
    build_result: MapBuildResult


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


__all__ = [
    "MapBuildApiRequest",
    "MapBuildResult",
    "ManualMapping",
    "ManualMappingCreate",
    "ManualMappingListResponse",
    "ManualMappingUpdate",
    "ProjectImportRequest",
    "ProjectImportResponse",
    "ScanCreateRequest",
    "ScanCreateResponse",
    "ScanProgressEvent",
    "ViewerLoadMapRequest",
    "ViewerPayload",
]
