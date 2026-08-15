"""Models for deterministic scanner file inventory."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from systograph.core.models.inventory_provenance import (
    InventoryPolicyAuditEntry,
)
from systograph.core.models.inventory_selection import (
    InventorySelectionSummary,
)
from systograph.core.models.scan import ScanModel


class FileInventorySource(StrEnum):
    """How the inventory candidate list was produced."""

    GIT = "git"
    RECURSIVE = "recursive"
    FALLBACK_AFTER_GIT_ERROR = "fallback_after_git_error"


class FileCategory(StrEnum):
    CODE = "code"
    CONFIG = "config"
    DOCS = "docs"
    INFRA = "infra"
    DATA = "data"
    SCRIPT = "script"
    MARKUP = "markup"


class SkipReason(StrEnum):
    """Why a project path was excluded from scanner inventory."""

    GITIGNORED = "gitignored"
    GIT_DIRECTORY = "git_directory"
    DEPENDENCY_DIRECTORY = "dependency_directory"
    VIRTUAL_ENV = "virtual_env"
    BUILD_OUTPUT = "build_output"
    CACHE_DIRECTORY = "cache_directory"
    COVERAGE_OUTPUT = "coverage_output"
    GENERATED = "generated"
    BINARY = "binary"
    LARGE_FILE = "large_file"
    LARGE_LOG = "large_log"
    MODEL_WEIGHT = "model_weight"
    SYMLINK_OUTSIDE_ROOT = "symlink_outside_root"
    UNREADABLE = "unreadable"
    SKIPPED_BY_POLICY_OVERLAY = "skipped_by_policy_overlay"
    PENDING_BOUNDARY_REVIEW = "pending_boundary_review"
    TEST_SUITE = "test_suite"


class FileRecord(ScanModel):
    """Eligible project file metadata."""

    path: str
    size_bytes: int
    language: str = "unknown"
    file_category: FileCategory = FileCategory.CODE
    size_lines: int = Field(default=0, ge=0)
    metadata_fingerprint: str | None = None
    content_fingerprint: str | None = None


class SkippedFile(ScanModel):
    """Skipped project path metadata."""

    path: str
    reason: SkipReason
    size_bytes: int | None = None


class FileInventory(ScanModel):
    """Deterministic inventory shared by downstream providers."""

    source: FileInventorySource
    project_root: str
    files: list[FileRecord] = Field(default_factory=list)
    skipped: list[SkippedFile] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    inventory_policy_schema_version: str | None = None
    inventory_policy_digest: str | None = None
    candidate_set_digest: str | None = None
    filesystem_safety_version: str | None = None
    boundary_decision_digest: str | None = None
    final_inventory_digest: str | None = None
    inventory_run_digest: str | None = None
    inventory_policy_audit: list[InventoryPolicyAuditEntry] = Field(
        default_factory=list
    )
    inventory_selection_summary: InventorySelectionSummary | None = None

    @property
    def files_scanned(self) -> int:
        return len(self.files)

    @property
    def files_skipped(self) -> int:
        return len(self.skipped)
