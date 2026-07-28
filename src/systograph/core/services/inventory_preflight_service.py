from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.inventory_selection import (
    InventoryCandidateOutcome,
    InventoryCandidatePage,
    InventoryPreflightRequest,
    InventoryPreflightState,
    InventoryPreflightSummary,
    InventoryRequestedTargetResult,
    InventoryRequestedTargetStatus,
    InventorySelectionScope,
)
from systograph.core.models.scan_boundary import ScanBoundaryDecisionRequest
from systograph.core.services.inventory_candidate_service import (
    MAX_RECURSIVE_DIRECTORY_BYTES,
    MAX_RECURSIVE_DIRECTORY_FILES,
    InventoryCandidateService,
)
from systograph.core.services.inventory_metadata_service import (
    InventoryMetadataService,
)
from systograph.core.services.inventory_preflight_cursor_service import (
    InventoryPreflightCursorService,
)
from systograph.core.services.inventory_preflight_limit_service import (
    MAX_DIRECTORY_SCOPES,
    MAX_REQUESTED_PATHS,
    MAX_REQUIRED_REVIEWS,
    InventoryPreflightLimitService,
)


class InventoryPreflightService:
    def __init__(
        self,
        *,
        candidate_service: InventoryCandidateService | None = None,
        max_requested_paths: int = MAX_REQUESTED_PATHS,
        max_directory_scopes: int = MAX_DIRECTORY_SCOPES,
        max_aggregate_files: int = MAX_RECURSIVE_DIRECTORY_FILES,
        max_aggregate_bytes: int = MAX_RECURSIVE_DIRECTORY_BYTES,
        max_required_reviews: int = MAX_REQUIRED_REVIEWS,
    ) -> None:
        self._candidates = candidate_service or InventoryCandidateService()
        self._metadata = InventoryMetadataService()
        self._cursor = InventoryPreflightCursorService()
        self._limits = InventoryPreflightLimitService(
            max_requested_paths=max_requested_paths,
            max_directory_scopes=max_directory_scopes,
            max_aggregate_files=max_aggregate_files,
            max_aggregate_bytes=max_aggregate_bytes,
            max_required_reviews=max_required_reviews,
        )

    def create(
        self,
        project_id: str,
        project_root: Path,
        request: InventoryPreflightRequest | Mapping[str, Any],
    ) -> InventoryPreflightState:
        parsed = (
            request
            if isinstance(request, InventoryPreflightRequest)
            else InventoryPreflightRequest.model_validate(request)
        )
        candidate_set = self._candidates.build_candidate_set(project_root)
        paths = self._normalized_paths(parsed.requested_paths)
        self._limits.validate_directory_scope_count(project_root, paths)
        results = tuple(
            self._candidates.resolve_requested_path(
                project_root,
                path,
                candidate_set=candidate_set,
            )
            for path in paths
        )
        self._limits.validate_results(results)
        self._limits.validate_required_reviews(candidate_set)
        request_id = self._metadata.preflight_request_id(
            project_id=project_id,
            source_mode=candidate_set.source_mode,
            candidate_set_digest=candidate_set.candidate_set_digest,
            inventory_policy_digest=candidate_set.inventory_policy_digest,
            filesystem_safety_version=(
                candidate_set.filesystem_safety_version
            ),
        )
        return InventoryPreflightState(
            project_id=project_id,
            preflight_request_id=request_id,
            candidate_set=candidate_set,
            requested_target_results=results,
        )

    def resolve_requested_path(
        self,
        project_root: Path,
        target_path: str,
    ) -> InventoryRequestedTargetResult:
        candidate_set = self._candidates.build_candidate_set(project_root)
        return self._candidates.resolve_requested_path(
            project_root,
            target_path,
            candidate_set=candidate_set,
        )

    def revalidate(
        self,
        project_id: str,
        project_root: Path,
        preflight_request_id: str,
        decisions: Iterable[ScanBoundaryDecisionRequest],
    ) -> InventoryPreflightState:
        decision_items = tuple(decisions)
        state = self.create(
            project_id,
            project_root,
            InventoryPreflightRequest(
                requested_paths=tuple(
                    item.target_path for item in decision_items
                )
            ),
        )
        if state.preflight_request_id != preflight_request_id:
            raise InventorySelectionError(
                InventorySelectionErrorCode.PREFLIGHT_STALE,
                http_status=409,
                retryable=True,
            )
        by_path = {
            item.target_path: item for item in state.requested_target_results
        }
        for decision in decision_items:
            result = by_path[decision.target_path]
            expected_scope = (
                InventorySelectionScope.RECURSIVE_DIRECTORY
                if result.directory_manifest is not None
                else InventorySelectionScope.EXACT_FILE
            )
            if decision.selection_scope != expected_scope:
                raise InventorySelectionError(
                    InventorySelectionErrorCode.SCOPE_INVALID
                )
        return state

    def reviewable_excluded_page(
        self,
        state: InventoryPreflightState,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> InventoryCandidatePage:
        return self._cursor.page(state, cursor=cursor, limit=limit)

    def summary(
        self, state: InventoryPreflightState
    ) -> InventoryPreflightSummary:
        candidates = state.candidate_set.candidates
        missing_paths = {
            item.path
            for item in candidates
            if item.base_outcome == InventoryCandidateOutcome.MISSING
        }
        missing_paths.update(
            item.target_path
            for item in state.requested_target_results
            if item.status == InventoryRequestedTargetStatus.MISSING
        )
        return InventoryPreflightSummary(
            default_included_file_count=sum(
                item.base_outcome == InventoryCandidateOutcome.INCLUDED
                for item in candidates
            ),
            required_review_count=sum(
                item.decision_required for item in candidates
            ),
            reviewable_excluded_count=sum(
                item.base_outcome == InventoryCandidateOutcome.SOFT_EXCLUDED
                for item in candidates
            ),
            hard_blocked_count=sum(
                item.base_outcome == InventoryCandidateOutcome.HARD_BLOCKED
                for item in candidates
            ),
            missing_count=len(missing_paths),
            collapsed_directory_count=len(
                state.candidate_set.skipped_summaries
            ),
        )

    def _normalized_paths(self, paths: tuple[str, ...]) -> tuple[str, ...]:
        self._limits.validate_path_count(paths)
        return tuple(
            sorted(
                {
                    self._candidates.normalize_requested_path(path)
                    for path in paths
                }
            )
        )
