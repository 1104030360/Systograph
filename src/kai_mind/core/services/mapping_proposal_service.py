"""Create pending mapping proposals from bounded evidence packets."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from pydantic import ValidationError

from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
    MappingCandidate,
    MappingCandidateType,
    MappingEvidencePacket,
    MappingProposal,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
    MappingProposalDecisionResult,
    MappingProposalStatus,
    MappingProviderCandidateBatch,
)
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.secret_masking_service import (
    SecretMaskingService,
)


class MappingProposalProvider(Protocol):
    """Optional provider boundary for LLM-assisted proposal candidates."""

    name: str

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        """Return raw JSON candidate output for KAI-Mind validation."""
        ...


class MappingProposalRepository(Protocol):
    """Storage boundary for proposal lifecycle state."""

    def save(self, proposal: MappingProposal) -> MappingProposal:
        """Create or replace one mapping proposal."""
        ...

    def get(self, proposal_id: str) -> MappingProposal | None:
        """Return one proposal by id."""
        ...

    def list_for_project(self, project_id: str) -> list[MappingProposal]:
        """Return all proposals for one project."""
        ...


class InMemoryMappingProposalRepository:
    """Process-local proposal repository for local API and tests."""

    def __init__(self) -> None:
        self._items: dict[str, MappingProposal] = {}

    def save(self, proposal: MappingProposal) -> MappingProposal:
        self._items[proposal.proposal_id] = proposal
        return proposal

    def get(self, proposal_id: str) -> MappingProposal | None:
        return self._items.get(proposal_id)

    def list_for_project(self, project_id: str) -> list[MappingProposal]:
        return sorted(
            [
                proposal
                for proposal in self._items.values()
                if proposal.project_id == project_id
            ],
            key=lambda item: item.created_at,
        )


class MappingProposalService:
    """Validate provider output and persist pending proposal drafts."""

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
        self._manual_mapping_service = manual_mapping_service
        self._secret_masking_service = (
            secret_masking_service or SecretMaskingService()
        )

    def create_proposal(
        self,
        packet: MappingEvidencePacket,
    ) -> MappingProposal:
        self._validate_packet(packet)
        candidates: list[MappingCandidate] | None = None
        provider_name = "deterministic"
        provider_error_reason: str | None = None

        if self._provider is not None:
            candidates, provider_error_reason = self._try_provider(packet)
            if candidates is not None:
                provider_name = self._provider.name

        if candidates is None:
            candidates = self._deterministic_candidates(packet)
            provider_name = "deterministic"

        now = _now()
        proposal = MappingProposal(
            proposal_id=f"proposal:{uuid4()}",
            project_id=packet.project_id,
            source_unmapped_id=packet.source_unmapped_id,
            status=MappingProposalStatus.PENDING,
            evidence_packet=packet,
            candidates=self._assign_candidate_ids(candidates),
            provider_name=provider_name,
            provider_error_reason=provider_error_reason,
            user_description=packet.user_description,
            created_at=now,
            updated_at=now,
        )
        return self._repository.save(proposal)

    def list_for_project(self, project_id: str) -> list[MappingProposal]:
        _require_text("project_id", project_id)
        return self._repository.list_for_project(project_id)

    @property
    def provider(self) -> MappingProposalProvider | None:
        return self._provider

    def decide(
        self,
        proposal_id: str,
        request: MappingProposalDecisionRequest,
    ) -> MappingProposalDecisionResult:
        proposal = self._repository.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)

        if request.decision == MappingProposalDecisionAction.REJECT:
            updated = self._with_status(
                proposal,
                MappingProposalStatus.REJECTED,
            )
            return MappingProposalDecisionResult(proposal=updated)

        if request.decision == MappingProposalDecisionAction.SKIP_FOR_NOW:
            updated = self._with_status(
                proposal,
                MappingProposalStatus.SKIPPED,
            )
            return MappingProposalDecisionResult(proposal=updated)

        manual_mapping = self._create_manual_mapping(proposal, request)
        status = (
            MappingProposalStatus.EDITED
            if request.decision == MappingProposalDecisionAction.EDIT
            else MappingProposalStatus.ACCEPTED
        )
        updated = self._with_status(proposal, status)
        return MappingProposalDecisionResult(
            proposal=updated,
            manual_mapping=manual_mapping,
        )

    def _try_provider(
        self,
        packet: MappingEvidencePacket,
    ) -> tuple[list[MappingCandidate] | None, str | None]:
        output_schema = MappingProviderCandidateBatch.model_json_schema()
        validation_error: str | None = None

        for _attempt in range(2):
            try:
                raw = self._provider.generate(  # type: ignore[union-attr]
                    packet=packet,
                    output_schema=output_schema,
                    validation_error=validation_error,
                )
                batch = MappingProviderCandidateBatch.model_validate_json(raw)
                candidates = self._validate_candidates(
                    packet,
                    batch.candidates,
                )
            except (ValidationError, ValueError) as exc:
                validation_error = self._safe_reason(str(exc))
                continue
            except Exception as exc:
                return None, self._safe_reason(str(exc))

            if candidates:
                return candidates, None
            validation_error = "Provider returned no candidates"

        return None, validation_error

    def _validate_packet(self, packet: MappingEvidencePacket) -> None:
        _require_text("project_id", packet.project_id)
        _require_text("source_unmapped_id", packet.source_unmapped_id)
        if not packet.evidence_ids:
            raise ValueError("MappingEvidencePacket must include evidence")
        self._reject_unmasked_secret(packet.model_dump(mode="json"))

    def _validate_candidates(
        self,
        packet: MappingEvidencePacket,
        candidates: Iterable[MappingCandidate],
    ) -> list[MappingCandidate]:
        validated: list[MappingCandidate] = []
        for candidate in candidates:
            self._validate_candidate(packet, candidate)
            validated.append(candidate)
        return sorted(validated, key=lambda item: item.rank)

    def _validate_candidate(
        self,
        packet: MappingEvidencePacket,
        candidate: MappingCandidate,
    ) -> None:
        if not candidate.evidence_ids:
            raise ValueError("candidate must include evidence")

        allowed_evidence = set(packet.evidence_ids)
        unknown_evidence = sorted(
            set(candidate.evidence_ids) - allowed_evidence
        )
        if unknown_evidence:
            raise ValueError(
                "candidate references unknown evidence: "
                f"{', '.join(unknown_evidence)}"
            )

        if candidate.candidate_type == MappingCandidateType.EXISTING_SLOT:
            if candidate.target_slot not in set(packet.available_slots):
                raise ValueError(
                    "candidate references unknown target slot: "
                    f"{candidate.target_slot}"
                )
        elif candidate.candidate_type == MappingCandidateType.NEW_EXTENSION:
            _require_text(
                "proposed_extension_id",
                candidate.proposed_extension_id,
            )
            _require_text(
                "proposed_extension_name",
                candidate.proposed_extension_name,
            )
            _require_text(
                "proposed_extension_kind",
                candidate.proposed_extension_kind,
            )

        self._validate_suggested_edges(packet, candidate)
        self._reject_unmasked_secret(candidate.model_dump(mode="json"))

    def _validate_suggested_edges(
        self,
        packet: MappingEvidencePacket,
        candidate: MappingCandidate,
    ) -> None:
        allowed = set(packet.available_slots)
        allowed.update(packet.available_extensions)
        allowed.update(packet.confirmed_component_ids)
        if candidate.proposed_extension_id is not None:
            allowed.add(candidate.proposed_extension_id)

        for edge in candidate.suggested_edges:
            source_missing = edge.source_ref not in allowed
            target_missing = edge.target_ref not in allowed
            if source_missing or target_missing:
                raise ValueError(
                    "candidate suggested edge references unknown endpoint"
                )

    def _reject_unmasked_secret(self, payload: object) -> None:
        serialized = json.dumps(payload, sort_keys=True)
        if self._secret_masking_service.contains_unmasked_secret(serialized):
            raise ValueError(
                "Proposal payload must not contain unmasked secret"
            )

    def _safe_reason(self, value: str) -> str:
        masked = self._secret_masking_service.mask_text(value)
        return masked[:400]

    def _deterministic_candidates(
        self,
        packet: MappingEvidencePacket,
    ) -> list[MappingCandidate]:
        text = _packet_text(packet)
        candidates: list[MappingCandidate] = []

        if "vector_store" in packet.available_slots and any(
            token in text
            for token in ("chroma", "qdrant", "faiss", "lancedb", "pgvector")
        ):
            candidates.append(
                MappingCandidate(
                    candidate_type=MappingCandidateType.EXISTING_SLOT,
                    target_slot="vector_store",
                    component_name=_vector_component_name(text),
                    component_kind="vector_db",
                    provider=_vector_provider(text),
                    label="Map evidence to Vector Store",
                    rationale=(
                        "Dependency or code evidence points to a vector "
                        "store client, but the baseline scanner marked it "
                        "as needing confirmation."
                    ),
                    evidence_ids=list(packet.evidence_ids),
                    rank=1,
                    recommendation_level="strong_candidate",
                    uncertainty_reason="Static evidence only.",
                )
            )

        if "router" in text or "route" in text:
            candidates.append(
                MappingCandidate(
                    candidate_type=MappingCandidateType.NEW_EXTENSION,
                    proposed_extension_id="extension:query_router",
                    proposed_extension_name="Query Router",
                    proposed_extension_kind="routing_orchestration",
                    label="Confirm Query Router as extension",
                    rationale=(
                        "Router-like evidence does not belong to a required "
                        "rag-core-v1 slot without user confirmation."
                    ),
                    evidence_ids=list(packet.evidence_ids),
                    rank=len(candidates) + 1,
                    recommendation_level="plausible_candidate",
                    uncertainty_reason="Task 20 does not prove runtime path.",
                )
            )

        if "rerank" in text:
            candidates.append(
                MappingCandidate(
                    candidate_type=MappingCandidateType.NEW_EXTENSION,
                    proposed_extension_id="extension:reranker",
                    proposed_extension_name="Reranker",
                    proposed_extension_kind="reranker",
                    label="Confirm Reranker as extension",
                    rationale=(
                        "Reranker-like evidence is an extension candidate "
                        "rather than a baseline rag-core-v1 slot."
                    ),
                    evidence_ids=list(packet.evidence_ids),
                    rank=len(candidates) + 1,
                    recommendation_level="plausible_candidate",
                    uncertainty_reason="Static evidence only.",
                )
            )

        candidates.append(
            MappingCandidate(
                candidate_type=MappingCandidateType.NEEDS_MORE_INFORMATION,
                label="Ask for more mapping context",
                rationale=(
                    "The bounded packet is not enough to safely confirm a "
                    "slot or extension."
                ),
                evidence_ids=list(packet.evidence_ids),
                rank=len(candidates) + 1,
                recommendation_level="needs_more_context",
                uncertainty_reason=(
                    "More user context or detail scan is needed."
                ),
            )
        )

        if len(candidates) < 3:
            candidates.append(
                MappingCandidate(
                    candidate_type=MappingCandidateType.SKIP_FOR_NOW,
                    label="Skip for now",
                    rationale=(
                        "Keep the component unmapped until stronger evidence "
                        "or user confirmation exists."
                    ),
                    evidence_ids=list(packet.evidence_ids),
                    rank=len(candidates) + 1,
                    recommendation_level="low_candidate",
                    uncertainty_reason=(
                        "Skipping does not change canonical map."
                    ),
                )
            )

        return candidates[:3]

    def _assign_candidate_ids(
        self,
        candidates: list[MappingCandidate],
    ) -> list[MappingCandidate]:
        return [
            candidate.model_copy(
                update={
                    "candidate_id": candidate.candidate_id
                    or f"candidate:{index}",
                }
            )
            for index, candidate in enumerate(candidates, start=1)
        ]

    def _create_manual_mapping(
        self,
        proposal: MappingProposal,
        request: MappingProposalDecisionRequest,
    ) -> ManualMapping:
        if self._manual_mapping_service is None:
            raise ValueError("manual_mapping_service is required")
        if request.decision == MappingProposalDecisionAction.EDIT:
            if request.edited_mapping is None:
                raise ValueError("edited_mapping is required for edit")
            draft = request.edited_mapping.model_copy(
                update={
                    "proposal_id": proposal.proposal_id,
                    "decision_source": "proposal_edit",
                }
            )
            return self._manual_mapping_service.create_mapping(draft)

        candidate = self._candidate_by_id(proposal, request.candidate_id)
        draft = self._candidate_to_manual_mapping(proposal, candidate)
        return self._manual_mapping_service.create_mapping(draft)

    def _candidate_by_id(
        self,
        proposal: MappingProposal,
        candidate_id: str | None,
    ) -> MappingCandidate:
        _require_text("candidate_id", candidate_id)
        for candidate in proposal.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"Unknown candidate_id: {candidate_id}")

    def _candidate_to_manual_mapping(
        self,
        proposal: MappingProposal,
        candidate: MappingCandidate,
    ) -> ManualMappingCreate:
        packet = proposal.evidence_packet
        if candidate.candidate_type == MappingCandidateType.EXISTING_SLOT:
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

        if candidate.candidate_type == MappingCandidateType.NEW_EXTENSION:
            return ManualMappingCreate(
                project_id=proposal.project_id,
                mapping_type=ManualMappingType.NEW_EXTENSION,
                decision=ManualMappingDecision.CONFIRMED,
                source_unmapped_id=proposal.source_unmapped_id,
                source_file=packet.source_file,
                observed_kind=packet.observed_kind,
                evidence_ids=list(candidate.evidence_ids),
                extension_id=candidate.proposed_extension_id,
                extension_name=candidate.proposed_extension_name,
                extension_kind=candidate.proposed_extension_kind,
                extension_edges=[
                    {
                        "from": edge.source_ref,
                        "to": edge.target_ref,
                        "relationship": edge.relationship,
                    }
                    for edge in candidate.suggested_edges
                ],
                proposal_id=proposal.proposal_id,
                decision_source="proposal_accept",
            )

        raise ValueError("Candidate cannot be accepted as manual mapping")

    def _with_status(
        self,
        proposal: MappingProposal,
        status: MappingProposalStatus,
    ) -> MappingProposal:
        updated = proposal.model_copy(
            update={
                "status": status,
                "updated_at": _now(),
            }
        )
        return self._repository.save(updated)


def _packet_text(packet: MappingEvidencePacket) -> str:
    return " ".join(
        [
            packet.observed_kind,
            packet.reason,
            " ".join(packet.rule_ids),
            " ".join(packet.masked_evidence_values),
            " ".join(packet.dependency_signals),
            " ".join(packet.import_signals),
            " ".join(packet.class_function_signals),
            " ".join(packet.call_like_signals),
        ]
    ).lower()


def _vector_component_name(text: str) -> str:
    if "chroma" in text:
        return "Chroma"
    if "qdrant" in text:
        return "Qdrant"
    if "pgvector" in text:
        return "pgvector"
    if "lancedb" in text:
        return "LanceDB"
    if "faiss" in text:
        return "FAISS"
    return "Vector Store"


def _vector_provider(text: str) -> str | None:
    if "chroma" in text:
        return "chroma"
    if "qdrant" in text:
        return "qdrant"
    if "pgvector" in text:
        return "pgvector"
    if "lancedb" in text:
        return "lancedb"
    if "faiss" in text:
        return "faiss"
    return None


def _require_text(field: str, value: str | None) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field} is required")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
