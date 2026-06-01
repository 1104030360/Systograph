"""Models for deterministic scanner file inventory."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from kai_mind.core.models.scan import ScanModel


class FileInventorySource(StrEnum):
    """How the inventory candidate list was produced."""

    GIT = "git"
    RECURSIVE = "recursive"
    FALLBACK_AFTER_GIT_ERROR = "fallback_after_git_error"


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


class FileRecord(ScanModel):
    """Eligible project file metadata."""

    path: str
    size_bytes: int


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

    @property
    def files_scanned(self) -> int:
        return len(self.files)

    @property
    def files_skipped(self) -> int:
        return len(self.skipped)
