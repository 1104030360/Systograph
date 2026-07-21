from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from kai_mind.core.models.inventory_selection import (
    DirectorySelectionManifest,
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryPreflightState,
    InventoryRequestedTargetStatus,
    InventorySelectionScope,
)
from kai_mind.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryEvidencePacket,
    ScanBoundaryProposal,
    ScanBoundaryProposalStatus,
    ScanBoundarySelectionContext,
    ScanBoundaryTarget,
)


class InventorySelectionProposalService:
    def create(
        self,
        state: InventoryPreflightState,
    ) -> list[ScanBoundaryProposal]:
        proposals: dict[
            tuple[str, InventorySelectionScope], ScanBoundaryProposal
        ] = {}
        for candidate in state.candidate_set.candidates:
            if candidate.decision_required or (
                candidate.base_outcome
                == InventoryCandidateOutcome.SOFT_EXCLUDED
            ):
                proposal = self.for_candidate(state.project_id, candidate)
                proposals[
                    (candidate.path, InventorySelectionScope.EXACT_FILE)
                ] = proposal
        for result in state.requested_target_results:
            if result.status != InventoryRequestedTargetStatus.REVIEWABLE:
                continue
            if result.file_candidate is not None:
                proposal = self.for_candidate(
                    state.project_id,
                    result.file_candidate,
                )
                proposals[
                    (result.target_path, InventorySelectionScope.EXACT_FILE)
                ] = proposal
            elif result.directory_manifest is not None:
                proposal = self.for_directory(
                    state.project_id,
                    result.directory_manifest,
                )
                proposals[
                    (
                        result.target_path,
                        InventorySelectionScope.RECURSIVE_DIRECTORY,
                    )
                ] = proposal
        return sorted(
            proposals.values(),
            key=lambda item: (
                item.target.path,
                item.selection_context.selection_scope
                if item.selection_context is not None
                else "",
            ),
        )

    def for_candidate(
        self,
        project_id: str,
        candidate: InventoryCandidate,
    ) -> ScanBoundaryProposal:
        required = candidate.decision_required
        base_outcome: Literal["included", "soft_excluded", "mixed"] = (
            "soft_excluded"
            if candidate.base_outcome
            == InventoryCandidateOutcome.SOFT_EXCLUDED
            else "included"
        )
        default_decision = (
            None
            if required
            else (
                ScanBoundaryDecisionAction.SKIP_THIS_RUN
                if candidate.base_outcome
                == InventoryCandidateOutcome.SOFT_EXCLUDED
                else ScanBoundaryDecisionAction.SCAN_THIS_RUN
            )
        )
        context = ScanBoundarySelectionContext(
            base_outcome=base_outcome,
            review_kind=(
                "required_confirmation" if required else "optional_override"
            ),
            default_decision=default_decision,
            decision_required=required,
            override_allowed=candidate.override_allowed,
            exclusion_sources=[
                item.value for item in candidate.exclusion_sources
            ],
            matched_inventory_policy_ids=list(
                candidate.matched_inventory_policy_ids
            ),
            target_kind="file",
            selection_scope=InventorySelectionScope.EXACT_FILE,
        )
        return self._proposal(
            project_id=project_id,
            target=ScanBoundaryTarget(
                path=candidate.path,
                target_type="file",
                risk_type=candidate.risk_type or "inventory_selection",
                reason=candidate.reason_code,
                size_bytes=candidate.size_bytes,
                fingerprint=candidate.metadata_fingerprint,
            ),
            context=context,
        )

    def for_directory(
        self,
        project_id: str,
        manifest: DirectorySelectionManifest,
    ) -> ScanBoundaryProposal:
        if manifest.soft_excluded_count == 0:
            base_outcome: Literal["included", "soft_excluded", "mixed"] = (
                "included"
            )
        elif manifest.default_included_count == 0:
            base_outcome = "soft_excluded"
        else:
            base_outcome = "mixed"
        context = ScanBoundarySelectionContext(
            base_outcome=base_outcome,
            review_kind="required_confirmation",
            default_decision=None,
            decision_required=True,
            override_allowed=True,
            exclusion_sources=sorted(
                {
                    source.value
                    for item in manifest.entries
                    for source in item.exclusion_sources
                }
            ),
            matched_inventory_policy_ids=sorted(
                {
                    policy_id
                    for item in manifest.entries
                    for policy_id in item.matched_inventory_policy_ids
                }
            ),
            target_kind="directory",
            selection_scope=InventorySelectionScope.RECURSIVE_DIRECTORY,
            directory_summary=manifest.summary(),
        )
        return self._proposal(
            project_id=project_id,
            target=ScanBoundaryTarget(
                path=manifest.directory_path,
                target_type="directory",
                risk_type="inventory_directory_selection",
                reason="recursive_directory_selection",
                size_bytes=None,
                fingerprint=manifest.manifest_fingerprint,
            ),
            context=context,
        )

    def _proposal(
        self,
        *,
        project_id: str,
        target: ScanBoundaryTarget,
        context: ScanBoundarySelectionContext,
    ) -> ScanBoundaryProposal:
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        proposal_id = self._proposal_id(
            project_id,
            target,
            context.selection_scope,
        )
        return ScanBoundaryProposal(
            proposal_id=proposal_id,
            project_id=project_id,
            status=ScanBoundaryProposalStatus.PENDING,
            target=target,
            evidence_packet=ScanBoundaryEvidencePacket(
                project_id=project_id,
                target_path=target.path,
                risk_type=target.risk_type,
                reason=target.reason,
                context_limits={
                    "metadata_only": True,
                    "raw_file_contents_included": False,
                    "project_root_included": False,
                },
            ),
            created_at=now,
            updated_at=now,
            selection_context=context,
        )

    def _proposal_id(
        self,
        project_id: str,
        target: ScanBoundaryTarget,
        scope: InventorySelectionScope,
    ) -> str:
        payload = ":".join(
            (project_id, target.path, scope.value, target.fingerprint)
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"scan-boundary-proposal:{digest[:32]}"
