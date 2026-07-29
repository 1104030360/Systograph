"""Scanner workflow models that are not part of ai-system-map/v2."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.inventory_provenance import (
    InventoryPolicyAuditEntry,
)
from kai_mind.core.models.inventory_selection import InventorySelectionSummary
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

    @property
    def profile_signals_path(self) -> Path:
        return self.root_dir / "profile_signals.json"

    @property
    def readiness_report_path(self) -> Path:
        return self.root_dir / "readiness_report.json"

    @property
    def call_graph_path(self) -> Path:
        return self.root_dir / "call_graph.json"

    @property
    def dataflow_hints_path(self) -> Path:
        return self.root_dir / "dataflow_hints.json"

    @property
    def execution_paths_path(self) -> Path:
        return self.root_dir / "execution_paths.json"

    @property
    def evidence_table_path(self) -> Path:
        return self.root_dir / "evidence_table.json"

    @property
    def system_map_mermaid_path(self) -> Path:
        return self.root_dir / "system_map.mmd"

    @property
    def execution_map_mermaid_path(self) -> Path:
        return self.root_dir / "execution_map.mmd"


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
    provider: str | None = None


class ParseIssue(ScanModel):
    """Structured parse failure that preserves partial scanner output."""

    provider: str
    scan_stage: Literal[
        "config_parse",
        "docker_compose_parse",
        "dependency_manifest_parse",
        "code_pattern_scan",
        "project_scan",
        "workflow_json_parse",
    ]
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


class SkippedFileSummary(ScanModel):
    """Project file skipped before provider collection."""

    path: str
    reason: str
    size_bytes: int | None = None


class ProjectScanResult(ScanModel):
    """Aggregated raw scanner output before component detection."""

    facts: list[ScanFact] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    issues: list[ParseIssue] = Field(default_factory=list)
    skipped_files: list[SkippedFileSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
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
    inventory_policy_audit: list[InventoryPolicyAuditEntry] = Field(
        default_factory=list
    )
    inventory_selection_summary: InventorySelectionSummary | None = None
