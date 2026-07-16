from __future__ import annotations

from pathlib import PurePosixPath

from kai_mind.core.models.inventory_provenance import (
    InventoryPolicyEffectiveOutcome,
)
from kai_mind.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryPreflightState,
    InventorySelectionScope,
)
from kai_mind.core.models.scan_boundary import ScanBoundaryDecisionAction
from kai_mind.core.services.inventory_selection_decision_service import (
    InventoryResolvedDecision,
)


class InventorySelectionPrecedenceService:
    def candidate_universe(
        self,
        state: InventoryPreflightState,
        decisions: tuple[InventoryResolvedDecision, ...],
    ) -> tuple[InventoryCandidate, ...]:
        candidates = {
            item.path: item for item in state.candidate_set.candidates
        }
        for decision in decisions:
            if decision.target.file_candidate is not None:
                candidate = decision.target.file_candidate
                candidates[candidate.path] = candidate
            elif decision.target.directory_manifest is not None:
                candidates.update(
                    {
                        item.path: item
                        for item in decision.target.directory_manifest.entries
                    }
                )
        return tuple(sorted(candidates.values(), key=lambda item: item.path))

    def winning_decision(
        self,
        path: str,
        decisions: tuple[InventoryResolvedDecision, ...],
    ) -> InventoryResolvedDecision | None:
        exact = next(
            (
                item
                for item in decisions
                if item.request.selection_scope
                == InventorySelectionScope.EXACT_FILE
                and item.request.target_path == path
            ),
            None,
        )
        if exact is not None:
            return exact
        directories = [
            item
            for item in decisions
            if item.request.selection_scope
            == InventorySelectionScope.RECURSIVE_DIRECTORY
            and item.target.directory_manifest is not None
            and any(
                candidate.path == path
                for candidate in item.target.directory_manifest.entries
            )
        ]
        return max(
            directories,
            key=lambda item: self._depth(item.request.target_path),
            default=None,
        )

    def planned_outcome(
        self,
        candidate: InventoryCandidate,
        decision: InventoryResolvedDecision | None,
    ) -> tuple[InventoryPolicyEffectiveOutcome, str]:
        if candidate.base_outcome == InventoryCandidateOutcome.MISSING:
            return (
                InventoryPolicyEffectiveOutcome.MISSING,
                candidate.reason_code,
            )
        if candidate.base_outcome == InventoryCandidateOutcome.HARD_BLOCKED:
            return (
                InventoryPolicyEffectiveOutcome.HARD_BLOCKED,
                candidate.reason_code,
            )
        if decision is not None:
            if decision.request.decision == (
                ScanBoundaryDecisionAction.SCAN_THIS_RUN
            ):
                return (
                    InventoryPolicyEffectiveOutcome.INCLUDED,
                    decision.request.decision.value,
                )
            return (
                InventoryPolicyEffectiveOutcome.SKIPPED,
                decision.request.decision.value,
            )
        if candidate.base_outcome == InventoryCandidateOutcome.INCLUDED:
            return (
                InventoryPolicyEffectiveOutcome.INCLUDED,
                candidate.reason_code,
            )
        return (
            InventoryPolicyEffectiveOutcome.SKIPPED,
            candidate.reason_code,
        )

    def _depth(self, path: str) -> int:
        return 0 if path == "." else len(PurePosixPath(path).parts)
