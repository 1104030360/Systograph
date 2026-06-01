"""Scanner workflow models that are not part of ai-system-map/v1."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.errors import PreconditionError


class ScanModel(BaseModel):
    """Base model that rejects silent scanner contract drift."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class OutputRun(ScanModel):
    """Resolved artifact paths for one map build run."""

    root_dir: Path

    @property
    def map_error_path(self) -> Path:
        return self.root_dir / "map-error.md"

    @property
    def map_json_path(self) -> Path:
        return self.root_dir / "ai_system_map.json"

    @property
    def map_markdown_path(self) -> Path:
        return self.root_dir / "ai_system_map.md"


class PreconditionResult(ScanModel):
    """Result of Stage 1 checks before any provider reads project files."""

    ok: bool
    project_root: Path | None = None
    output_run: OutputRun | None = None
    warnings: list[str] = Field(default_factory=list)
    error: PreconditionError | None = None

    @property
    def output_run_dir(self) -> Path | None:
        if self.output_run is None:
            return None
        return self.output_run.root_dir
