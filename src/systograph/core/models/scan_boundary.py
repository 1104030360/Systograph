"""Domain models for same-run scan boundary review."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from systograph.core.models.inventory_selection import (
    DirectorySelectionSummary,
    InventorySelectionScope,
)
from systograph.core.models.scan import ScanModel

MAX_BOUNDARY_REASON_CHARS = 800
MAX_BOUNDARY_EVIDENCE_VALUES = 12
MAX_BOUNDARY_EVIDENCE_VALUE_CHARS = 240
MAX_BOUNDARY_EVIDENCE_SNIPPETS = 6
MAX_BOUNDARY_EVIDENCE_SNIPPET_CHARS = 500


class ScanBoundaryProposalStatus(StrEnum):
    """Lifecycle state for a scan boundary proposal."""

    PENDING = "pending_user_confirmation"


class ScanBoundaryDecisionAction(StrEnum):
    """Supported one-run user decisions for scan policy overlay."""

    SCAN_THIS_RUN = "scan_this_run"
    SKIP_THIS_RUN = "skip_this_run"


class ScanBoundaryTarget(ScanModel):
    """Project-relative target that may need scan boundary confirmation."""

    path: str
    target_type: str = "file"
    risk_type: str
    reason: str = Field(max_length=MAX_BOUNDARY_REASON_CHARS)
    size_bytes: int | None = None
    fingerprint: str


class ScanBoundaryEvidencePacket(ScanModel):
    """Bounded, masked context used to review one boundary proposal."""

    project_id: str
    target_path: str
    risk_type: str
    reason: str = Field(max_length=MAX_BOUNDARY_REASON_CHARS)
    evidence_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    masked_evidence_values: list[str] = Field(
        default_factory=list,
        max_length=MAX_BOUNDARY_EVIDENCE_VALUES,
    )
    masked_snippets: list[str] = Field(
        default_factory=list,
        max_length=MAX_BOUNDARY_EVIDENCE_SNIPPETS,
    )
    context_limits: dict[str, str | int | bool] = Field(default_factory=dict)


class ScanBoundarySelectionContext(ScanModel):
    base_outcome: Literal["included", "soft_excluded", "mixed"]
    review_kind: Literal["required_confirmation", "optional_override"]
    default_decision: ScanBoundaryDecisionAction | None = None
    decision_required: bool
    override_allowed: bool
    exclusion_sources: list[str] = Field(default_factory=list)
    matched_inventory_policy_ids: list[str] = Field(default_factory=list)
    target_kind: Literal["file", "directory"]
    selection_scope: InventorySelectionScope
    directory_summary: DirectorySelectionSummary | None = None


class ScanBoundaryProposal(ScanModel):
    """Pending user confirmation before the current scan can continue."""

    proposal_id: str
    project_id: str
    status: ScanBoundaryProposalStatus
    target: ScanBoundaryTarget
    evidence_packet: ScanBoundaryEvidencePacket
    available_actions: list[ScanBoundaryDecisionAction] = Field(
        default_factory=lambda: [
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
        ]
    )
    created_at: str
    updated_at: str
    selection_context: ScanBoundarySelectionContext | None = None


class ScanBoundaryDecisionRequest(ScanModel):
    """One scan-run decision payload for one boundary target."""

    target_path: str
    fingerprint: str
    decision: ScanBoundaryDecisionAction
    selection_scope: InventorySelectionScope = (
        InventorySelectionScope.EXACT_FILE
    )
    reason: str | None = Field(
        default=None,
        max_length=MAX_BOUNDARY_REASON_CHARS,
    )
