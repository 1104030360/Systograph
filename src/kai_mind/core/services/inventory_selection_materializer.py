from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
    SkippedFile,
)
from kai_mind.core.models.inventory_provenance import (
    InventoryPolicyAuditEntry,
    InventoryPolicyEffectiveOutcome,
)
from kai_mind.core.models.inventory_selection import (
    InventoryPreflightState,
    InventorySelectionScope,
    InventorySelectionSummary,
)
from kai_mind.core.models.scan_boundary import (
    ScanBoundaryProposal,
)
from kai_mind.core.services.inventory_post_decision_safety_service import (
    InventoryPostDecisionSafetyService,
)
from kai_mind.core.services.inventory_provenance_service import (
    InventoryProvenanceService,
)
from kai_mind.core.services.inventory_selection_audit_service import (
    InventorySelectionAuditService,
)
from kai_mind.core.services.inventory_selection_decision_service import (
    InventoryResolvedDecision,
)
from kai_mind.core.services.inventory_selection_precedence_service import (
    InventorySelectionPrecedenceService,
)
from kai_mind.core.services.inventory_selection_proposal_service import (
    InventorySelectionProposalService,
)
from kai_mind.core.services.inventory_selection_result_service import (
    InventorySelectionResultService,
)


@dataclass(frozen=True, slots=True)
class InventorySelectionMaterialization:
    inventory: FileInventory | None
    pending_proposals: tuple[ScanBoundaryProposal, ...]
    summary: InventorySelectionSummary


class InventorySelectionMaterializer:
    def __init__(
        self,
        *,
        safety_service: InventoryPostDecisionSafetyService | None = None,
    ) -> None:
        self._safety = safety_service or InventoryPostDecisionSafetyService()
        self._audit = InventorySelectionAuditService()
        self._provenance = InventoryProvenanceService()
        self._proposals = InventorySelectionProposalService()
        self._precedence = InventorySelectionPrecedenceService()
        self._results = InventorySelectionResultService()

    def materialize(
        self,
        *,
        project_root: Path,
        state: InventoryPreflightState,
        decisions: tuple[InventoryResolvedDecision, ...],
    ) -> InventorySelectionMaterialization:
        candidates = self._precedence.candidate_universe(state, decisions)
        pending = tuple(
            self._proposals.for_candidate(state.project_id, candidate)
            for candidate in candidates
            if candidate.decision_required
            and self._precedence.winning_decision(candidate.path, decisions)
            is None
        )
        if pending:
            return InventorySelectionMaterialization(
                inventory=None,
                pending_proposals=pending,
                summary=InventorySelectionSummary(
                    included_file_count=0,
                    skipped_file_count=0,
                ),
            )

        files: list[FileRecord] = []
        skipped: list[SkippedFile] = []
        audit: list[InventoryPolicyAuditEntry] = []
        included_by_directory: dict[str, int] = {}
        post_blocked_by_directory: dict[str, int] = {}
        for candidate in candidates:
            decision = self._precedence.winning_decision(
                candidate.path,
                decisions,
            )
            effective, reason = self._precedence.planned_outcome(
                candidate,
                decision,
            )
            if effective == InventoryPolicyEffectiveOutcome.INCLUDED:
                safety = self._safety.check(project_root, candidate)
                if not safety.allowed:
                    self._raise_exact_block(decision, safety.changed)
                    effective = InventoryPolicyEffectiveOutcome.HARD_BLOCKED
                    reason = safety.reason_code or "post_decision_blocked"
                    if (
                        decision is not None
                        and self._results.is_directory_decision(decision)
                    ):
                        path = decision.request.target_path
                        post_blocked_by_directory[path] = (
                            post_blocked_by_directory.get(path, 0) + 1
                        )
                else:
                    files.append(
                        FileRecord(
                            path=candidate.path,
                            size_bytes=candidate.size_bytes or 0,
                            metadata_fingerprint=(
                                candidate.metadata_fingerprint
                            ),
                            content_fingerprint=(safety.content_fingerprint),
                        )
                    )
                    if (
                        decision is not None
                        and self._results.is_directory_decision(decision)
                    ):
                        path = decision.request.target_path
                        included_by_directory[path] = (
                            included_by_directory.get(path, 0) + 1
                        )
            if effective != InventoryPolicyEffectiveOutcome.INCLUDED:
                skipped.append(
                    SkippedFile(
                        path=candidate.path,
                        reason=self._results.skip_reason(
                            candidate,
                            decision,
                            reason,
                        ),
                        size_bytes=candidate.size_bytes,
                    )
                )
            audit.append(
                self._audit.entry(
                    state=state,
                    candidate=candidate,
                    decision=decision,
                    effective_outcome=effective,
                    reason_code=reason,
                )
            )

        directory_results = self._results.directory_results(
            decisions,
            included_by_directory=included_by_directory,
            post_blocked_by_directory=post_blocked_by_directory,
        )
        self._results.require_scannable_directories(directory_results)
        self._results.add_collapsed_summaries(state, decisions, skipped)
        summary = InventorySelectionSummary(
            included_file_count=len(files),
            skipped_file_count=sum(
                item.audit_scope.value == "path"
                and item.effective_outcome
                != InventoryPolicyEffectiveOutcome.INCLUDED
                for item in audit
            ),
            directory_scope_results=directory_results,
        )
        inventory = FileInventory(
            source=FileInventorySource(state.candidate_set.source_mode),
            project_root=str(project_root.resolve()),
            files=sorted(files, key=lambda item: item.path),
            skipped=sorted(
                skipped,
                key=lambda item: (item.path, item.reason.value),
            ),
            warnings=list(state.candidate_set.warnings),
            inventory_policy_schema_version=(
                state.candidate_set.inventory_policy_schema_version
            ),
            inventory_policy_digest=(
                state.candidate_set.inventory_policy_digest
            ),
            candidate_set_digest=state.candidate_set.candidate_set_digest,
            filesystem_safety_version=(
                state.candidate_set.filesystem_safety_version
            ),
            inventory_policy_audit=audit,
            inventory_selection_summary=summary,
        )
        inventory = self._provenance.finalize_boundary(
            inventory,
            audit=audit,
        )
        return InventorySelectionMaterialization(
            inventory=inventory,
            pending_proposals=(),
            summary=summary,
        )

    def _raise_exact_block(
        self,
        decision: InventoryResolvedDecision | None,
        changed: bool,
    ) -> None:
        if decision is None or decision.request.selection_scope != (
            InventorySelectionScope.EXACT_FILE
        ):
            return
        raise InventorySelectionError(
            (
                InventorySelectionErrorCode.TARGET_CHANGED
                if changed
                else InventorySelectionErrorCode.POST_DECISION_BLOCKED
            ),
            http_status=409 if changed else 422,
            retryable=changed,
        )
