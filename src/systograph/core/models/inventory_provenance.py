from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InventoryPolicyAuditOutcome(StrEnum):
    INCLUDED = "included"
    SKIPPED = "skipped"
    PENDING_REVIEW = "pending_review"


class InventoryPolicyAuditSource(StrEnum):
    PROJECT_IGNORE = "project_ignore"
    FILESYSTEM_SAFETY = "filesystem_safety"
    SYSTOGRAPH_INVENTORY_CATALOG = "systograph_inventory_catalog"
    RUNTIME_BOUNDARY = "runtime_boundary"


class InventoryPolicyAuditScope(StrEnum):
    PATH = "path"
    DIRECTORY_SUMMARY = "directory_summary"


class InventoryPolicyBaseOutcome(StrEnum):
    INCLUDED = "included"
    SOFT_EXCLUDED = "soft_excluded"
    HARD_BLOCKED = "hard_blocked"
    MISSING = "missing"


class InventoryPolicyEffectiveOutcome(StrEnum):
    INCLUDED = "included"
    SKIPPED = "skipped"
    HARD_BLOCKED = "hard_blocked"
    MISSING = "missing"


class InventoryPolicyDecisionOrigin(StrEnum):
    DEFAULT_POLICY = "default_policy"
    RUNTIME_USER_DECISION = "runtime_user_decision"


class InventoryPolicyAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    outcome: InventoryPolicyAuditOutcome
    source: InventoryPolicyAuditSource
    source_mode: Literal[
        "git",
        "recursive",
        "fallback_after_git_error",
    ]
    audit_scope: InventoryPolicyAuditScope
    reason: str
    matched_inventory_policy_ids: list[str] = Field(default_factory=list)
    effective_inventory_policy_id: str | None = None
    matched_pattern: str | None = None
    boundary_decision: str | None = None
    target_fingerprint: str | None = None
    base_outcome: InventoryPolicyBaseOutcome | None = None
    effective_outcome: InventoryPolicyEffectiveOutcome | None = None
    decision_origin: InventoryPolicyDecisionOrigin | None = None
    decision_target_path: str | None = None
    decision_scope: Literal["exact_file", "recursive_directory"] | None = None
    decision_fingerprint: str | None = None
    override_applied: bool | None = None
    preflight_request_id: str | None = None
