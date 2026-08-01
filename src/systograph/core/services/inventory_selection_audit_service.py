from __future__ import annotations

from systograph.core.models.inventory_provenance import (
    InventoryPolicyAuditEntry,
    InventoryPolicyAuditOutcome,
    InventoryPolicyAuditScope,
    InventoryPolicyAuditSource,
    InventoryPolicyBaseOutcome,
    InventoryPolicyDecisionOrigin,
    InventoryPolicyEffectiveOutcome,
)
from systograph.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryPreflightState,
    InventorySelectionSource,
)
from systograph.core.services.inventory_selection_decision_service import (
    InventoryResolvedDecision,
)


class InventorySelectionAuditService:
    def entry(
        self,
        *,
        state: InventoryPreflightState,
        candidate: InventoryCandidate,
        decision: InventoryResolvedDecision | None,
        effective_outcome: InventoryPolicyEffectiveOutcome,
        reason_code: str,
    ) -> InventoryPolicyAuditEntry:
        return InventoryPolicyAuditEntry(
            path=candidate.path,
            outcome=(
                InventoryPolicyAuditOutcome.INCLUDED
                if effective_outcome
                == InventoryPolicyEffectiveOutcome.INCLUDED
                else InventoryPolicyAuditOutcome.SKIPPED
            ),
            source=self._source(candidate, decision),
            source_mode=state.candidate_set.source_mode,
            audit_scope=InventoryPolicyAuditScope.PATH,
            reason=reason_code,
            matched_inventory_policy_ids=list(
                candidate.matched_inventory_policy_ids
            ),
            effective_inventory_policy_id=(
                candidate.effective_inventory_policy_id
            ),
            boundary_decision=(
                decision.request.decision.value
                if decision is not None
                else None
            ),
            target_fingerprint=(
                decision.request.fingerprint if decision is not None else None
            ),
            base_outcome=InventoryPolicyBaseOutcome(
                candidate.base_outcome.value
            ),
            effective_outcome=effective_outcome,
            decision_origin=(
                InventoryPolicyDecisionOrigin.RUNTIME_USER_DECISION
                if decision is not None
                else InventoryPolicyDecisionOrigin.DEFAULT_POLICY
            ),
            decision_target_path=(
                decision.request.target_path if decision is not None else None
            ),
            decision_scope=(
                decision.request.selection_scope.value
                if decision is not None
                else None
            ),
            decision_fingerprint=(
                decision.request.fingerprint if decision is not None else None
            ),
            override_applied=self._override_applied(
                candidate,
                decision,
                effective_outcome,
            ),
            preflight_request_id=state.preflight_request_id,
        )

    def _source(
        self,
        candidate: InventoryCandidate,
        decision: InventoryResolvedDecision | None,
    ) -> InventoryPolicyAuditSource:
        if candidate.base_outcome in {
            InventoryCandidateOutcome.HARD_BLOCKED,
            InventoryCandidateOutcome.MISSING,
        }:
            return InventoryPolicyAuditSource.FILESYSTEM_SAFETY
        if decision is not None:
            return InventoryPolicyAuditSource.RUNTIME_BOUNDARY
        if (
            InventorySelectionSource.FILESYSTEM_SAFETY
            in candidate.exclusion_sources
        ):
            return InventoryPolicyAuditSource.FILESYSTEM_SAFETY
        if any(
            source
            in {
                InventorySelectionSource.PROJECT_IGNORE,
                InventorySelectionSource.GIT_PRIVATE_EXCLUDE,
                InventorySelectionSource.GIT_GLOBAL_EXCLUDE,
            }
            for source in candidate.exclusion_sources
        ):
            return InventoryPolicyAuditSource.PROJECT_IGNORE
        return InventoryPolicyAuditSource.SYSTOGRAPH_INVENTORY_CATALOG

    def _override_applied(
        self,
        candidate: InventoryCandidate,
        decision: InventoryResolvedDecision | None,
        effective_outcome: InventoryPolicyEffectiveOutcome,
    ) -> bool:
        if decision is None:
            return False
        return (
            candidate.base_outcome == InventoryCandidateOutcome.INCLUDED
            and effective_outcome != InventoryPolicyEffectiveOutcome.INCLUDED
        ) or (
            candidate.base_outcome == InventoryCandidateOutcome.SOFT_EXCLUDED
            and effective_outcome == InventoryPolicyEffectiveOutcome.INCLUDED
        )
