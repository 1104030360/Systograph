"""Models for core map build orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.models.viewer import ViewerLoadResult


class MapBuildModel(BaseModel):
    """Base model for map build inputs and results."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class MapBuildRequest(MapBuildModel):
    project_path: Path
    output: Path = Path("outputs")
    redact_root_path: bool = True
    no_snippets: bool = False


class MapBuildResult(MapBuildModel):
    status: Literal["ok", "error"]
    project_name: str
    output_run_dir: Path | None = None
    map_json_path: Path | None = None
    map_error_path: Path | None = None
    viewer_load_result: ViewerLoadResult | None = None
    ai_system_map: RagSystemMap | None = None
    warnings: list[str] = Field(default_factory=list)
    error: PreconditionError | None = None
