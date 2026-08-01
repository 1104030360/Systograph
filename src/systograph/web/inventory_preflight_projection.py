from __future__ import annotations

from datetime import UTC, datetime

from systograph.core.models.inventory_selection import (
    InventoryCandidateOutcome,
    InventoryPreflightRequest,
    InventoryPreflightState,
    InventoryRequestedTargetStatus,
    InventorySelectionScope,
)
from systograph.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from systograph.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from systograph.web.schemas import (
    InventoryBlockedSummaryView,
    InventoryPreflightResponse,
    InventoryRequestedTargetView,
    InventoryReviewableExcludedPageView,
)


def project_inventory_preflight(
    state: InventoryPreflightState,
    request: InventoryPreflightRequest,
    *,
    preflight_service: InventoryPreflightService,
    boundary_service: ScanBoundaryReviewService,
) -> InventoryPreflightResponse:
    proposals = boundary_service.create_selection_proposals(state)
    by_target = {
        (
            proposal.target.path,
            proposal.selection_context.selection_scope,
        ): proposal
        for proposal in proposals
        if proposal.selection_context is not None
    }
    page = preflight_service.reviewable_excluded_page(
        state,
        cursor=request.reviewable_excluded_cursor,
        limit=request.reviewable_excluded_limit,
    )
    required = [
        by_target[(candidate.path, InventorySelectionScope.EXACT_FILE)]
        for candidate in state.candidate_set.candidates
        if candidate.decision_required
    ]
    requested_views = []
    for result in state.requested_target_results:
        proposal = None
        if result.status == InventoryRequestedTargetStatus.REVIEWABLE:
            scope = (
                InventorySelectionScope.RECURSIVE_DIRECTORY
                if result.directory_manifest is not None
                else InventorySelectionScope.EXACT_FILE
            )
            proposal = by_target[(result.target_path, scope)]
        requested_views.append(
            InventoryRequestedTargetView(
                target_path=result.target_path,
                target_kind=result.target_kind,
                status=result.status,
                proposal=proposal,
                reason_code=result.reason_code,
                limit_context=result.limit_context,
            )
        )
    blocked = [
        InventoryBlockedSummaryView(
            path=candidate.path,
            reason_code=candidate.reason_code,
            outcome="hard_blocked",
        )
        for candidate in state.candidate_set.candidates
        if candidate.base_outcome == InventoryCandidateOutcome.HARD_BLOCKED
    ]
    blocked.extend(
        InventoryBlockedSummaryView(
            path=summary.path,
            reason_code=summary.reason_code,
            outcome="collapsed_directory",
            can_expand=summary.can_expand,
        )
        for summary in state.candidate_set.skipped_summaries
    )
    candidate_set = state.candidate_set
    return InventoryPreflightResponse(
        preflight_request_id=state.preflight_request_id,
        project_id=state.project_id,
        generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        source_mode=candidate_set.source_mode,
        inventory_policy_schema_version=(
            candidate_set.inventory_policy_schema_version
        ),
        inventory_policy_digest=candidate_set.inventory_policy_digest,
        candidate_set_digest=candidate_set.candidate_set_digest,
        filesystem_safety_version=candidate_set.filesystem_safety_version,
        summary=preflight_service.summary(state),
        required_boundary_proposals=required,
        reviewable_excluded_page=InventoryReviewableExcludedPageView(
            items=[
                by_target[(candidate.path, InventorySelectionScope.EXACT_FILE)]
                for candidate in page.items
            ],
            next_cursor=page.next_cursor,
            total=page.total,
        ),
        requested_target_results=requested_views,
        blocked_summaries=sorted(blocked, key=lambda item: item.path),
        warnings=list(candidate_set.warnings),
    )
