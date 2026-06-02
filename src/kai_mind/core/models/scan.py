"""Scanner workflow models that are not part of ai-system-map/v1."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.system_map import Evidence


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


class ScanFact(ScanModel):
    """Low-level scanner fact emitted before slot/component mapping."""

    kind: str
    file: str
    path: str
    value: str | None = None
    rule_id: str | None = None


class ParseIssue(ScanModel):
    """Structured parse failure that preserves partial scanner output."""

    provider: str
    scan_stage: Literal["config_parse", "docker_compose_parse"]
    file: str
    message: str
    rule_id: str
    line: int | None = None
    column: int | None = None


class ProviderScanResult(ScanModel):
    """Shared provider-local output before higher-level normalization."""

    facts: list[ScanFact] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    issues: list[ParseIssue] = Field(default_factory=list)
