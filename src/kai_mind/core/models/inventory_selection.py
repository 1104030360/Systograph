from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InventorySelectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InventoryCandidateOutcome(StrEnum):
    INCLUDED = "included"
    SOFT_EXCLUDED = "soft_excluded"
    HARD_BLOCKED = "hard_blocked"
    MISSING = "missing"


class InventorySelectionSource(StrEnum):
    PROJECT_IGNORE = "project_ignore"
    GIT_PRIVATE_EXCLUDE = "git_private_exclude"
    GIT_GLOBAL_EXCLUDE = "git_global_exclude"
    KAI_INVENTORY_CATALOG = "kai_inventory_catalog"
    FILESYSTEM_SAFETY = "filesystem_safety"
    RUNTIME_USER_DECISION = "runtime_user_decision"


class InventoryTargetKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"


class InventorySelectionScope(StrEnum):
    EXACT_FILE = "exact_file"
    RECURSIVE_DIRECTORY = "recursive_directory"


class InventoryRequestedTargetStatus(StrEnum):
    REVIEWABLE = "reviewable"
    HARD_BLOCKED = "hard_blocked"
    MISSING = "missing"
    EMPTY_DIRECTORY = "empty_directory"
    DIRECTORY_LIMIT_EXCEEDED = "directory_limit_exceeded"


class InventoryDirectoryLimitKind(StrEnum):
    DIRECTORY_SCOPE_COUNT = "directory_scope_count"
    OBSERVED_FILE_COUNT = "observed_file_count"
    SELECTABLE_BYTES = "selectable_bytes"
    RELATIVE_DEPTH = "relative_depth"
    AGGREGATE_OBSERVED_FILE_COUNT = "aggregate_observed_file_count"
    AGGREGATE_SELECTABLE_BYTES = "aggregate_selectable_bytes"


class InventoryDirectoryLimitContext(InventorySelectionModel):
    limit_kind: InventoryDirectoryLimitKind
    limit: int
    observed_at_least: int


class InventoryCandidate(InventorySelectionModel):
    path: str
    target_kind: Literal[InventoryTargetKind.FILE] = InventoryTargetKind.FILE
    target_type: str
    size_bytes: int | None
    mtime_ns: int | None
    base_outcome: InventoryCandidateOutcome
    exclusion_sources: tuple[InventorySelectionSource, ...] = ()
    matched_inventory_policy_ids: tuple[str, ...] = ()
    effective_inventory_policy_id: str | None = None
    reason_code: str
    risk_type: str | None = None
    decision_required: bool
    override_allowed: bool
    metadata_fingerprint: str


class DirectorySelectionSummary(InventorySelectionModel):
    observed_regular_file_count: int
    selectable_file_count: int
    default_included_count: int
    soft_excluded_count: int
    sensitive_file_count: int
    pre_content_hard_blocked_count: int
    selectable_bytes: int
    observed_max_relative_depth: int
    blocked_reason_counts: dict[str, int] = Field(default_factory=dict)


class DirectorySelectionManifest(DirectorySelectionSummary):
    directory_path: str
    selection_scope: Literal[InventorySelectionScope.RECURSIVE_DIRECTORY] = (
        InventorySelectionScope.RECURSIVE_DIRECTORY
    )
    entries: tuple[InventoryCandidate, ...]
    manifest_fingerprint: str

    @classmethod
    def from_entries(
        cls,
        *,
        directory_path: str,
        entries: tuple[InventoryCandidate, ...],
        manifest_fingerprint: str,
    ) -> DirectorySelectionManifest:
        ordered = tuple(sorted(entries, key=lambda item: item.path))
        selectable = tuple(
            item
            for item in ordered
            if item.base_outcome
            in {
                InventoryCandidateOutcome.INCLUDED,
                InventoryCandidateOutcome.SOFT_EXCLUDED,
            }
        )
        blocked_reason_counts: dict[str, int] = {}
        for item in ordered:
            if item.base_outcome != InventoryCandidateOutcome.HARD_BLOCKED:
                continue
            blocked_reason_counts[item.reason_code] = (
                blocked_reason_counts.get(item.reason_code, 0) + 1
            )
        base_depth = (
            0
            if directory_path == "."
            else len(PurePosixPath(directory_path).parts)
        )
        max_depth = max(
            (
                len(PurePosixPath(item.path).parts) - base_depth
                for item in ordered
            ),
            default=0,
        )
        return cls(
            directory_path=directory_path,
            observed_regular_file_count=sum(
                item.target_type == "regular_file" for item in ordered
            ),
            selectable_file_count=len(selectable),
            default_included_count=sum(
                item.base_outcome == InventoryCandidateOutcome.INCLUDED
                for item in ordered
            ),
            soft_excluded_count=sum(
                item.base_outcome == InventoryCandidateOutcome.SOFT_EXCLUDED
                for item in ordered
            ),
            sensitive_file_count=sum(
                item.risk_type is not None for item in ordered
            ),
            pre_content_hard_blocked_count=sum(
                item.base_outcome == InventoryCandidateOutcome.HARD_BLOCKED
                for item in ordered
            ),
            selectable_bytes=sum(item.size_bytes or 0 for item in selectable),
            observed_max_relative_depth=max_depth,
            blocked_reason_counts=blocked_reason_counts,
            entries=ordered,
            manifest_fingerprint=manifest_fingerprint,
        )

    def summary(self) -> DirectorySelectionSummary:
        return DirectorySelectionSummary.model_validate(
            self.model_dump(
                exclude={
                    "directory_path",
                    "selection_scope",
                    "entries",
                    "manifest_fingerprint",
                }
            )
        )


class InventoryDirectorySummary(InventorySelectionModel):
    path: str
    reason_code: str
    exclusion_source: InventorySelectionSource
    can_expand: bool = True


class InventoryRequestedTargetResult(InventorySelectionModel):
    target_path: str
    target_kind: InventoryTargetKind
    status: InventoryRequestedTargetStatus
    file_candidate: InventoryCandidate | None = None
    directory_manifest: DirectorySelectionManifest | None = None
    reason_code: str | None = None
    limit_context: InventoryDirectoryLimitContext | None = None


class InventoryCandidateSet(InventorySelectionModel):
    source_mode: Literal[
        "git",
        "recursive",
        "fallback_after_git_error",
    ]
    candidates: tuple[InventoryCandidate, ...]
    skipped_summaries: tuple[InventoryDirectorySummary, ...] = ()
    warnings: tuple[str, ...] = ()
    inventory_policy_schema_version: str
    inventory_policy_digest: str
    filesystem_safety_version: str
    candidate_set_digest: str


class InventoryPreflightRequest(InventorySelectionModel):
    scan_depth: Literal["system"] = "system"
    requested_paths: tuple[str, ...] = Field(default_factory=tuple)
    reviewable_excluded_cursor: str | None = None
    reviewable_excluded_limit: int = Field(default=100, ge=1, le=200)


class InventoryPreflightState(InventorySelectionModel):
    project_id: str
    preflight_request_id: str
    candidate_set: InventoryCandidateSet
    requested_target_results: tuple[InventoryRequestedTargetResult, ...] = ()


class InventoryPreflightSummary(InventorySelectionModel):
    default_included_file_count: int
    required_review_count: int
    reviewable_excluded_count: int
    hard_blocked_count: int
    missing_count: int
    collapsed_directory_count: int


class InventoryCandidatePage(InventorySelectionModel):
    items: tuple[InventoryCandidate, ...]
    next_cursor: str | None = None
    total: int


class InventoryDirectoryScopeResult(InventorySelectionModel):
    target_path: str
    decision: Literal["scan_this_run", "skip_this_run"]
    observed_file_count: int
    included_file_count: int
    hard_blocked_file_count: int
    post_decision_blocked_file_count: int


class InventorySelectionSummary(InventorySelectionModel):
    included_file_count: int
    skipped_file_count: int
    directory_scope_results: tuple[InventoryDirectoryScopeResult, ...] = ()
