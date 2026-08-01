"""Structured error models for deterministic scanner failures."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ErrorModel(BaseModel):
    """Base model that rejects silent error contract drift."""

    model_config = ConfigDict(extra="forbid")


class PreconditionFailureReason(StrEnum):
    """Fatal reasons detected before provider scanning starts."""

    PROJECT_PATH_NOT_FOUND = "project_path_not_found"
    PROJECT_PATH_NOT_DIRECTORY = "project_path_not_directory"
    PROJECT_PATH_NOT_READABLE = "project_path_not_readable"
    OUTPUT_DIRECTORY_NOT_WRITABLE = "output_directory_not_writable"


class PreconditionError(ErrorModel):
    """Structured data used to render the human-readable error artifact."""

    project_path: str
    failure_reason: PreconditionFailureReason
    scan_stage: Literal["precondition"] = "precondition"


class ScanInventoryRulesErrorCode(StrEnum):
    UNAVAILABLE = "inventory_rules_unavailable"
    INVALID = "inventory_rules_invalid"


class InventoryEnumerationErrorCode(StrEnum):
    FAILED = "inventory_enumeration_failed"


class ScanInventoryRulesError(Exception):
    def __init__(self, code: ScanInventoryRulesErrorCode) -> None:
        self.code = code
        super().__init__(code.value)

    def __str__(self) -> str:
        return self.code.value


class InventoryEnumerationError(Exception):
    def __init__(self) -> None:
        self.code = InventoryEnumerationErrorCode.FAILED
        super().__init__(self.code.value)

    def __str__(self) -> str:
        return self.code.value


class InventorySelectionErrorCode(StrEnum):
    PATH_INVALID = "inventory_selection_path_invalid"
    SCOPE_INVALID = "inventory_selection_scope_invalid"
    DUPLICATE_DECISION = "inventory_selection_duplicate_decision"
    CONFLICTING_DECISION = "inventory_selection_conflicting_decision"
    OVERRIDE_NOT_ALLOWED = "inventory_selection_override_not_allowed"
    DIRECTORY_LIMIT_EXCEEDED = "inventory_selection_directory_limit_exceeded"
    DIRECTORY_NO_SCANNABLE_FILES = (
        "inventory_selection_directory_no_scannable_files"
    )
    REVIEW_LIMIT_EXCEEDED = "inventory_preflight_review_limit_exceeded"
    PREFLIGHT_STALE = "inventory_preflight_stale"
    TARGET_MISSING = "inventory_selection_target_missing"
    TARGET_CHANGED = "inventory_selection_target_changed"
    POST_DECISION_BLOCKED = "inventory_selection_post_decision_blocked"
    CURSOR_INVALID = "inventory_preflight_cursor_invalid"


class InventorySelectionError(Exception):
    def __init__(
        self,
        code: InventorySelectionErrorCode,
        *,
        http_status: int = 422,
        retryable: bool = False,
        context: dict[str, str | int] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.retryable = retryable
        self.context = context
        super().__init__(code.value)

    def __str__(self) -> str:
        return self.code.value
