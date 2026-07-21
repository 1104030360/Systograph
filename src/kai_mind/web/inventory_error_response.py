from __future__ import annotations

from kai_mind.core.models.errors import (
    InventoryEnumerationError,
    InventorySelectionError,
    InventorySelectionErrorCode,
    ScanInventoryRulesError,
)
from kai_mind.web.schemas import InventoryApiErrorDetail

ERROR_MESSAGES = {
    InventorySelectionErrorCode.PATH_INVALID: (
        "Choose a project-relative path without glob syntax."
    ),
    InventorySelectionErrorCode.SCOPE_INVALID: (
        "The selection scope does not match the current target type."
    ),
    InventorySelectionErrorCode.DUPLICATE_DECISION: (
        "Each selection target can be decided only once."
    ),
    InventorySelectionErrorCode.CONFLICTING_DECISION: (
        "The same selection target has conflicting decisions."
    ),
    InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED: (
        "This target cannot be overridden for the current scan."
    ),
    InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED: (
        "Choose fewer or smaller directory scopes."
    ),
    InventorySelectionErrorCode.DIRECTORY_NO_SCANNABLE_FILES: (
        "The selected directory has no files that can be scanned safely."
    ),
    InventorySelectionErrorCode.REVIEW_LIMIT_EXCEEDED: (
        "The scan requires too many boundary reviews."
    ),
    InventorySelectionErrorCode.PREFLIGHT_STALE: (
        "Scan selection changed. Refresh the file review."
    ),
    InventorySelectionErrorCode.TARGET_MISSING: (
        "The selected target no longer exists."
    ),
    InventorySelectionErrorCode.TARGET_CHANGED: (
        "The selected target changed. Refresh the file review."
    ),
    InventorySelectionErrorCode.POST_DECISION_BLOCKED: (
        "The selected file did not pass content safety checks."
    ),
    InventorySelectionErrorCode.CURSOR_INVALID: (
        "Refresh the excluded-file review page."
    ),
}


def inventory_error_detail(
    error: InventorySelectionError,
) -> dict[str, object]:
    return InventoryApiErrorDetail(
        code=error.code.value,
        message=ERROR_MESSAGES[error.code],
        retryable=error.retryable,
        context=error.context,
    ).model_dump(mode="json")


def project_not_found_detail() -> dict[str, object]:
    return InventoryApiErrorDetail(
        code="project_not_found",
        message="Project not found.",
        retryable=False,
    ).model_dump(mode="json")


def inventory_system_error_detail(
    error: InventoryEnumerationError | ScanInventoryRulesError,
) -> dict[str, object]:
    message = (
        "Inventory enumeration could not be completed safely."
        if isinstance(error, InventoryEnumerationError)
        else "Inventory policy could not be loaded safely."
    )
    return InventoryApiErrorDetail(
        code=error.code.value,
        message=message,
        retryable=False,
    ).model_dump(mode="json")
