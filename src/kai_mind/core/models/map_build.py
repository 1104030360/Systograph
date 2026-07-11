"""Models for core map build orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.analysis_history import MapBuildLineage
from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.models.readiness_report import ReadinessReport
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.models.viewer import ViewerLoadResult

SystemMapSchemaSelection = Literal["ai-system-map/v1", "ai-system-map/v2"]


class MapBuildModel(BaseModel):
    """Base model for map build inputs and results."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MapBuildRequest(MapBuildModel):
    project_path: Path
    output: Path = Path("outputs")
    redact_root_path: bool = True
    no_snippets: bool = False
    system_map_schema_version: SystemMapSchemaSelection = "ai-system-map/v1"


class MapBuildResult(MapBuildModel):
    status: Literal["ok", "error"]
    project_name: str
    output_run_dir: Path | None = None
    map_json_path: Path | None = None
    map_markdown_path: Path | None = None
    map_error_path: Path | None = None
    profile_signals_path: Path | None = None
    readiness_report_path: Path | None = None
    call_graph_path: Path | None = None
    dataflow_hints_path: Path | None = None
    execution_paths_path: Path | None = None
    evidence_table_path: Path | None = None
    system_map_mermaid_path: Path | None = None
    execution_map_mermaid_path: Path | None = None
    viewer_load_result: ViewerLoadResult | None = None
    ai_system_map: RagSystemMap | None = None
    normalized_ai_system_map: AiSystemMapV2 | None = None
    profile_inference_result: ProfileInferenceResult | None = None
    readiness_report: ReadinessReport | None = None
    lineage: MapBuildLineage | None = None
    active_schema_version: SystemMapSchemaSelection = "ai-system-map/v1"
    requested_schema_version: SystemMapSchemaSelection = "ai-system-map/v1"
    migration_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: PreconditionError | None = None
