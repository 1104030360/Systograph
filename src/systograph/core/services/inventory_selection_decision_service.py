from __future__ import annotations

from dataclasses import dataclass

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.inventory_selection import (
    InventoryPreflightState,
    InventoryRequestedTargetResult,
    InventoryRequestedTargetStatus,
    InventorySelectionScope,
)
from systograph.core.models.scan_boundary import ScanBoundaryDecisionRequest
from systograph.core.services.inventory_candidate_service import (
    InventoryCandidateService,
)


@dataclass(frozen=True, slots=True)
class InventoryResolvedDecision:
    request: ScanBoundaryDecisionRequest
    target: InventoryRequestedTargetResult


class InventorySelectionDecisionService:
    def __init__(
        self,
        *,
        candidate_service: InventoryCandidateService | None = None,
    ) -> None:
        self._candidates = candidate_service or InventoryCandidateService()

    def normalize(
        self,
        decisions: tuple[ScanBoundaryDecisionRequest, ...],
    ) -> tuple[ScanBoundaryDecisionRequest, ...]:
        normalized: list[ScanBoundaryDecisionRequest] = []
        seen: dict[
            tuple[str, InventorySelectionScope],
            ScanBoundaryDecisionRequest,
        ] = {}
        for decision in decisions:
            path = self._candidates.normalize_requested_path(
                decision.target_path
            )
            item = decision.model_copy(update={"target_path": path})
            key = (path, item.selection_scope)
            prior = seen.get(key)
            if prior is not None:
                code = (
                    InventorySelectionErrorCode.CONFLICTING_DECISION
                    if prior.decision != item.decision
                    else InventorySelectionErrorCode.DUPLICATE_DECISION
                )
                raise InventorySelectionError(code)
            seen[key] = item
            normalized.append(item)
        return tuple(normalized)

    def resolve(
        self,
        state: InventoryPreflightState,
        decisions: tuple[ScanBoundaryDecisionRequest, ...],
    ) -> tuple[InventoryResolvedDecision, ...]:
        by_path = {
            item.target_path: item for item in state.requested_target_results
        }
        resolved: list[InventoryResolvedDecision] = []
        for decision in decisions:
            target = by_path[decision.target_path]
            self._validate_target(decision, target)
            resolved.append(
                InventoryResolvedDecision(request=decision, target=target)
            )
        return tuple(resolved)

    def _validate_target(
        self,
        decision: ScanBoundaryDecisionRequest,
        target: InventoryRequestedTargetResult,
    ) -> None:
        if target.status == InventoryRequestedTargetStatus.MISSING:
            raise InventorySelectionError(
                InventorySelectionErrorCode.TARGET_MISSING,
                http_status=409,
                retryable=True,
            )
        if target.status == (
            InventoryRequestedTargetStatus.DIRECTORY_LIMIT_EXCEEDED
        ):
            context = (
                target.limit_context.model_dump(mode="json")
                if target.limit_context is not None
                else None
            )
            raise InventorySelectionError(
                InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED,
                context=context,
            )
        if target.status != InventoryRequestedTargetStatus.REVIEWABLE:
            raise InventorySelectionError(
                InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED
            )
        if target.file_candidate is not None:
            expected_scope = InventorySelectionScope.EXACT_FILE
            expected_fingerprint = target.file_candidate.metadata_fingerprint
            if not target.file_candidate.override_allowed:
                raise InventorySelectionError(
                    InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED
                )
        elif target.directory_manifest is not None:
            expected_scope = InventorySelectionScope.RECURSIVE_DIRECTORY
            expected_fingerprint = (
                target.directory_manifest.manifest_fingerprint
            )
        else:
            raise InventorySelectionError(
                InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED
            )
        if decision.selection_scope != expected_scope:
            raise InventorySelectionError(
                InventorySelectionErrorCode.SCOPE_INVALID
            )
        if decision.fingerprint != expected_fingerprint:
            raise InventorySelectionError(
                InventorySelectionErrorCode.TARGET_CHANGED,
                http_status=409,
                retryable=True,
            )
