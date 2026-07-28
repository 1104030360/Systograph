from __future__ import annotations

from typing import assert_never

from systograph.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
    MappingCandidate,
    MappingCandidateType,
    MappingProposal,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.mapping_proposal_support import now, require_text


class ProposalManualMappingFactory:
    def __init__(
        self,
        manual_mapping_service: ManualMappingService | None,
    ) -> None:
        self._manual_mapping_service = manual_mapping_service

    def create_confirmed(
        self,
        proposal: MappingProposal,
        request: MappingProposalDecisionRequest,
    ) -> ManualMapping:
        service = self._manual_mapping_service_or_raise()
        self._reject_duplicate_confirmed_mapping(proposal, service)
        if request.decision == MappingProposalDecisionAction.EDIT:
            edited_mapping = request.edited_mapping
            if edited_mapping is None:
                raise ValueError("edited_mapping is required for edit")
            self._validate_edited_mapping_scope(proposal, edited_mapping)
            return service.create_mapping(
                edited_mapping.model_copy(
                    update={
                        "project_id": proposal.project_id,
                        "source_unmapped_id": proposal.source_unmapped_id,
                        "source_file": proposal.evidence_packet.source_file,
                        "observed_kind": (
                            proposal.evidence_packet.observed_kind
                        ),
                        "proposal_id": proposal.proposal_id,
                        "decision_source": "proposal_edit",
                    }
                )
            )
        candidate = self._candidate_by_id(proposal, request.candidate_id)
        return service.create_mapping(
            self._candidate_to_manual_mapping(proposal, candidate)
        )

    def create_audit(
        self,
        proposal: MappingProposal,
        request: MappingProposalDecisionRequest,
        *,
        decision: ManualMappingDecision,
    ) -> ManualMapping:
        draft = ManualMappingCreate(
            project_id=proposal.project_id,
            mapping_type=self._audit_mapping_type(proposal),
            decision=decision,
            source_unmapped_id=proposal.source_unmapped_id,
            source_file=proposal.evidence_packet.source_file,
            observed_kind=proposal.evidence_packet.observed_kind,
            evidence_ids=list(proposal.evidence_packet.evidence_ids),
            reason=request.reason,
            proposal_id=proposal.proposal_id,
            decision_source=f"proposal_{request.decision.value}",
            audit_metadata={
                "acted_at": now(),
                "actor_surface": "mapping_proposal",
            },
        )
        return self._manual_mapping_service_or_raise().create_mapping(draft)

    def _audit_mapping_type(
        self,
        proposal: MappingProposal,
    ) -> ManualMappingType:
        for candidate in proposal.candidates:
            match candidate.candidate_type:
                case MappingCandidateType.EXISTING_SLOT:
                    return ManualMappingType.EXISTING_SLOT
                case MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE:
                    return ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
                case (
                    MappingCandidateType.NEEDS_MORE_INFORMATION
                    | MappingCandidateType.SKIP_FOR_NOW
                ):
                    continue
                case unreachable:
                    assert_never(unreachable)
        return ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE

    def _candidate_to_manual_mapping(
        self,
        proposal: MappingProposal,
        candidate: MappingCandidate,
    ) -> ManualMappingCreate:
        packet = proposal.evidence_packet
        match candidate.candidate_type:
            case MappingCandidateType.EXISTING_SLOT:
                return ManualMappingCreate(
                    project_id=proposal.project_id,
                    mapping_type=ManualMappingType.EXISTING_SLOT,
                    decision=ManualMappingDecision.CONFIRMED,
                    source_unmapped_id=proposal.source_unmapped_id,
                    source_file=packet.source_file,
                    observed_kind=packet.observed_kind,
                    evidence_ids=list(candidate.evidence_ids),
                    target_slot=candidate.target_slot,
                    component_name=candidate.component_name or candidate.label,
                    component_kind=(
                        candidate.component_kind or packet.observed_kind
                    ),
                    provider=candidate.provider,
                    proposal_id=proposal.proposal_id,
                    decision_source="proposal_accept",
                )
            case MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE:
                return ManualMappingCreate(
                    project_id=proposal.project_id,
                    mapping_type=(
                        ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
                    ),
                    decision=ManualMappingDecision.CONFIRMED,
                    source_unmapped_id=proposal.source_unmapped_id,
                    source_file=packet.source_file,
                    observed_kind=packet.observed_kind,
                    evidence_ids=list(candidate.evidence_ids),
                    capability_candidate_id=(
                        candidate.proposed_capability_candidate_id
                    ),
                    capability_candidate_name=(
                        candidate.proposed_capability_candidate_name
                    ),
                    capability_candidate_kind=(
                        candidate.proposed_capability_candidate_kind
                    ),
                    proposal_id=proposal.proposal_id,
                    decision_source="proposal_accept",
                )
            case (
                MappingCandidateType.NEEDS_MORE_INFORMATION
                | MappingCandidateType.SKIP_FOR_NOW
            ):
                raise ValueError(
                    "Candidate cannot be accepted as manual mapping"
                )
            case unreachable:
                assert_never(unreachable)

    def _validate_edited_mapping_scope(
        self,
        proposal: MappingProposal,
        edited_mapping: ManualMappingCreate,
    ) -> None:
        unknown_evidence = sorted(
            set(edited_mapping.evidence_ids)
            - set(proposal.evidence_packet.evidence_ids)
        )
        if unknown_evidence:
            raise ValueError(
                "edited_mapping references unknown evidence: "
                f"{', '.join(unknown_evidence)}"
            )

    def _reject_duplicate_confirmed_mapping(
        self,
        proposal: MappingProposal,
        service: ManualMappingService,
    ) -> None:
        for mapping in service.list_for_project(proposal.project_id):
            if (
                mapping.source_unmapped_id == proposal.source_unmapped_id
                and mapping.decision == ManualMappingDecision.CONFIRMED
            ):
                raise ValueError(
                    "source_unmapped_id already has confirmed mapping"
                )

    def _candidate_by_id(
        self,
        proposal: MappingProposal,
        candidate_id: str | None,
    ) -> MappingCandidate:
        candidate_id = require_text("candidate_id", candidate_id)
        for candidate in proposal.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"Unknown candidate_id: {candidate_id}")

    def _manual_mapping_service_or_raise(self) -> ManualMappingService:
        if self._manual_mapping_service is None:
            raise ValueError("manual_mapping_service is required")
        return self._manual_mapping_service
