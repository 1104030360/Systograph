from __future__ import annotations

from threading import RLock
from uuid import uuid4

from systograph.core.models.mapping import (
    MappingEvidencePacket,
    MappingProposal,
    MappingProposalDecisionRequest,
    MappingProposalDecisionResult,
    MappingProposalStatus,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.mapping_proposal_candidates import (
    ProposalCandidateFactory,
)
from systograph.core.services.mapping_proposal_decisions import (
    MappingProposalDecisionService,
)
from systograph.core.services.mapping_proposal_provider import (
    MappingProposalProvider,
    MappingProposalProviderUnavailableError,
)
from systograph.core.services.mapping_proposal_repository import (
    InMemoryMappingProposalRepository,
    MappingProposalRepository,
)
from systograph.core.services.mapping_proposal_support import now, require_text
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


class MappingProposalService:
    def __init__(
        self,
        *,
        repository: MappingProposalRepository | None = None,
        provider: MappingProposalProvider | None = None,
        manual_mapping_service: ManualMappingService | None = None,
        secret_masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._repository = repository or InMemoryMappingProposalRepository()
        self._provider = provider
        candidate_factory = ProposalCandidateFactory(
            secret_masking_service or SecretMaskingService()
        )
        self._candidate_factory = candidate_factory
        self._decision_service = MappingProposalDecisionService(
            repository=self._repository,
            manual_mapping_service=manual_mapping_service,
        )
        self._decision_lock = RLock()

    def create_proposal(
        self,
        packet: MappingEvidencePacket,
    ) -> MappingProposal:
        self._candidate_factory.validate_packet(packet)
        existing = self._pending_proposal_for_source(packet)
        if existing is not None:
            return existing
        candidates, provider_error_reason = (
            self._candidate_factory.provider_candidates(self._provider, packet)
        )
        provider_name = "deterministic"
        if candidates is None:
            candidates = self._candidate_factory.deterministic_candidates(
                packet
            )
        elif self._provider is not None:
            provider_name = self._provider.name
        created_at = now()
        return self._repository.save(
            MappingProposal(
                proposal_id=f"proposal:{uuid4()}",
                project_id=packet.project_id,
                source_unmapped_id=packet.source_unmapped_id,
                status=MappingProposalStatus.PENDING,
                evidence_packet=packet,
                candidates=self._candidate_factory.assign_candidate_ids(
                    candidates
                ),
                provider_name=provider_name,
                provider_error_reason=provider_error_reason,
                user_description=packet.user_description,
                created_at=created_at,
                updated_at=created_at,
            )
        )

    def list_for_project(self, project_id: str) -> list[MappingProposal]:
        require_text("project_id", project_id)
        return self._repository.list_for_project(project_id)

    @property
    def provider(self) -> MappingProposalProvider | None:
        return self._provider

    def decide(
        self,
        proposal_id: str,
        request: MappingProposalDecisionRequest,
    ) -> MappingProposalDecisionResult:
        with self._decision_lock:
            proposal = self._repository.get(proposal_id)
            if proposal is None:
                raise KeyError(proposal_id)
            if proposal.status != MappingProposalStatus.PENDING:
                raise ValueError(
                    f"Proposal is not pending: {proposal.status.value}"
                )
            return self._decision_service.decide(proposal, request)

    def _pending_proposal_for_source(
        self,
        packet: MappingEvidencePacket,
    ) -> MappingProposal | None:
        for proposal in self._repository.list_for_project(packet.project_id):
            if (
                proposal.source_unmapped_id == packet.source_unmapped_id
                and proposal.status == MappingProposalStatus.PENDING
            ):
                return proposal
        return None


__all__ = [
    "InMemoryMappingProposalRepository",
    "MappingProposalProvider",
    "MappingProposalProviderUnavailableError",
    "MappingProposalRepository",
    "MappingProposalService",
]
