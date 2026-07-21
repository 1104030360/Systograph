from __future__ import annotations

from kai_mind.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from kai_mind.core.models.filesystem import SkippedFile, SkipReason
from kai_mind.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryDirectoryScopeResult,
    InventoryPreflightState,
    InventorySelectionScope,
    InventorySelectionSource,
)
from kai_mind.core.models.scan_boundary import ScanBoundaryDecisionAction
from kai_mind.core.services.inventory_selection_decision_service import (
    InventoryResolvedDecision,
)


class InventorySelectionResultService:
    def skip_reason(
        self,
        candidate: InventoryCandidate,
        decision: InventoryResolvedDecision | None,
        reason: str,
    ) -> SkipReason:
        if decision is not None and decision.request.decision == (
            ScanBoundaryDecisionAction.SKIP_THIS_RUN
        ):
            return SkipReason.SKIPPED_BY_POLICY_OVERLAY
        if any(
            source
            in {
                InventorySelectionSource.PROJECT_IGNORE,
                InventorySelectionSource.GIT_PRIVATE_EXCLUDE,
                InventorySelectionSource.GIT_GLOBAL_EXCLUDE,
            }
            for source in candidate.exclusion_sources
        ):
            return SkipReason.GITIGNORED
        aliases = {
            "absolute_size_cap": SkipReason.LARGE_FILE,
            "symlink_not_allowed": SkipReason.SYMLINK_OUTSIDE_ROOT,
            "unsupported_file_type": SkipReason.UNREADABLE,
            "target_changed": SkipReason.UNREADABLE,
        }
        if reason in aliases:
            return aliases[reason]
        try:
            return SkipReason(reason)
        except ValueError:
            return SkipReason.UNREADABLE

    def directory_results(
        self,
        decisions: tuple[InventoryResolvedDecision, ...],
        *,
        included_by_directory: dict[str, int],
        post_blocked_by_directory: dict[str, int],
    ) -> tuple[InventoryDirectoryScopeResult, ...]:
        results = []
        for decision in decisions:
            manifest = decision.target.directory_manifest
            if manifest is None:
                continue
            path = decision.request.target_path
            results.append(
                InventoryDirectoryScopeResult(
                    target_path=path,
                    decision=decision.request.decision.value,
                    observed_file_count=manifest.observed_regular_file_count,
                    included_file_count=included_by_directory.get(path, 0),
                    hard_blocked_file_count=(
                        manifest.pre_content_hard_blocked_count
                    ),
                    post_decision_blocked_file_count=(
                        post_blocked_by_directory.get(path, 0)
                    ),
                )
            )
        return tuple(sorted(results, key=lambda item: item.target_path))

    def require_scannable_directories(
        self,
        results: tuple[InventoryDirectoryScopeResult, ...],
    ) -> None:
        for result in results:
            if (
                result.decision
                == ScanBoundaryDecisionAction.SCAN_THIS_RUN.value
                and result.included_file_count == 0
            ):
                raise InventorySelectionError(
                    InventorySelectionErrorCode.DIRECTORY_NO_SCANNABLE_FILES
                )

    def add_collapsed_summaries(
        self,
        state: InventoryPreflightState,
        decisions: tuple[InventoryResolvedDecision, ...],
        skipped: list[SkippedFile],
    ) -> None:
        selected = {
            item.request.target_path
            for item in decisions
            if item.request.selection_scope
            == InventorySelectionScope.RECURSIVE_DIRECTORY
        }
        for summary in state.candidate_set.skipped_summaries:
            if any(
                path == "."
                or summary.path == path
                or summary.path.startswith(f"{path}/")
                for path in selected
            ):
                continue
            skipped.append(
                SkippedFile(
                    path=f"{summary.path}/",
                    reason=self._summary_reason(summary.reason_code),
                )
            )

    def is_directory_decision(
        self,
        decision: InventoryResolvedDecision | None,
    ) -> bool:
        return decision is not None and decision.request.selection_scope == (
            InventorySelectionScope.RECURSIVE_DIRECTORY
        )

    def _summary_reason(self, reason: str) -> SkipReason:
        try:
            return SkipReason(reason)
        except ValueError:
            return SkipReason.GITIGNORED
