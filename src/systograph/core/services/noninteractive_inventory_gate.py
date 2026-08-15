from __future__ import annotations

from pathlib import Path
from typing import Never

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.filesystem import FileInventory
from systograph.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryPreflightRequest,
)
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
)
from systograph.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from systograph.core.services.inventory_selection_service import (
    InventorySelectionService,
)


class NonInteractiveInventoryGate:
    def __init__(
        self,
        *,
        preflight_service: InventoryPreflightService | None = None,
        selection_service: InventorySelectionService | None = None,
        approve_boundary_review: bool = False,
    ) -> None:
        self._preflight = preflight_service or InventoryPreflightService()
        self._selection = selection_service or InventorySelectionService(
            preflight_service=self._preflight
        )
        # Operator-supplied consent for this run: the reviewable
        # candidates are approved with the same one-run decisions the
        # Web flow submits, so provenance still records a runtime user
        # decision per path. Hard-blocked paths stay blocked -- a test
        # suite or a path-safety violation is not reviewable at all.
        self._approve_boundary_review = approve_boundary_review

    def select(
        self,
        *,
        project_id: str,
        project_root: Path,
    ) -> FileInventory:
        state = self._preflight.create(
            project_id,
            project_root,
            InventoryPreflightRequest(),
        )
        reviewable = tuple(
            candidate
            for candidate in state.candidate_set.candidates
            if candidate.decision_required
        )
        if reviewable and not self._approve_boundary_review:
            self._raise_review_required()
        result = self._selection.select(
            project_id=project_id,
            project_root=project_root,
            preflight_request_id=state.preflight_request_id,
            decisions=self._approvals(reviewable),
        )
        if result.inventory is None or result.pending_proposals:
            self._raise_review_required()
        return result.inventory

    def _approvals(
        self,
        reviewable: tuple[InventoryCandidate, ...],
    ) -> tuple[ScanBoundaryDecisionRequest, ...]:
        if not self._approve_boundary_review:
            return ()
        return tuple(
            ScanBoundaryDecisionRequest(
                target_path=candidate.path,
                fingerprint=candidate.metadata_fingerprint,
                decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
                reason="approved by operator on the command line",
            )
            for candidate in reviewable
        )

    def _raise_review_required(self) -> Never:
        raise InventorySelectionError(
            InventorySelectionErrorCode.NON_INTERACTIVE_REVIEW_REQUIRED,
            context={"resolution": "use_web_review_flow"},
        )
