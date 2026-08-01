from __future__ import annotations

from typing import assert_never

from systograph.core.models.mapping import (
    ManualMapping,
    ManualMappingDecision,
    MappingProposal,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
    MappingProposalDecisionResult,
    MappingProposalStatus,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.mapping_proposal_mapping_factory import (
    ProposalManualMappingFactory,
)
from systograph.core.services.mapping_proposal_repository import (
    MappingProposalRepository,
)
from systograph.core.services.mapping_proposal_support import now


class MappingProposalDecisionService:
    def __init__(
        self,
        *,
        repository: MappingProposalRepository,
        manual_mapping_service: ManualMappingService | None,
    ) -> None:
        self._repository = repository
        self._mapping_factory = ProposalManualMappingFactory(
            manual_mapping_service
        )

    def decide(
        self,
        proposal: MappingProposal,
        request: MappingProposalDecisionRequest,
    ) -> MappingProposalDecisionResult:
        match request.decision:
            case MappingProposalDecisionAction.REJECT:
                return self._finish(
                    proposal,
                    MappingProposalStatus.REJECTED,
                    self._mapping_factory.create_audit(
                        proposal,
                        request,
                        decision=ManualMappingDecision.REJECTED,
                    ),
                )
            case MappingProposalDecisionAction.SKIP_FOR_NOW:
                return self._finish(
                    proposal,
                    MappingProposalStatus.SKIPPED,
                    self._mapping_factory.create_audit(
                        proposal,
                        request,
                        decision=ManualMappingDecision.SKIP_FOR_NOW,
                    ),
                )
            case (
                MappingProposalDecisionAction.ACCEPT
                | MappingProposalDecisionAction.EDIT
            ):
                status = (
                    MappingProposalStatus.EDITED
                    if request.decision == MappingProposalDecisionAction.EDIT
                    else MappingProposalStatus.ACCEPTED
                )
                return self._finish(
                    proposal,
                    status,
                    self._mapping_factory.create_confirmed(proposal, request),
                )
            case unreachable:
                assert_never(unreachable)

    def _finish(
        self,
        proposal: MappingProposal,
        status: MappingProposalStatus,
        manual_mapping: ManualMapping,
    ) -> MappingProposalDecisionResult:
        updated = proposal.model_copy(
            update={
                "status": status,
                "updated_at": now(),
            }
        )
        return MappingProposalDecisionResult(
            proposal=self._repository.save(updated),
            manual_mapping=manual_mapping,
        )
