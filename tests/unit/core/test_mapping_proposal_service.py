from __future__ import annotations

import json

from kai_mind.core.models.mapping import (
    MappingCandidate,
    MappingCandidateType,
    MappingEvidencePacket,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
    MappingProposalStatus,
)
from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingService,
)
from kai_mind.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalProvider,
    MappingProposalService,
)


class InvalidConfidenceProvider:
    name = "invalid-confidence"

    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        self.calls += 1
        return json.dumps(
            {
                "candidates": [
                    {
                        "candidate_type": "existing_slot_mapping",
                        "target_slot": "vector_store",
                        "label": "Map to vector store",
                        "rationale": "The dependency is chromadb.",
                        "evidence_ids": ["evidence:chromadb"],
                        "rank": 1,
                        "recommendation_level": "strong_candidate",
                        "confidence": 0.91,
                    }
                ]
            }
        )


class HallucinatedReferenceProvider:
    name = "hallucinated-reference"

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        return json.dumps(
            {
                "candidates": [
                    {
                        "candidate_type": "existing_slot_mapping",
                        "target_slot": "missing_slot",
                        "label": "Bad slot",
                        "rationale": "This references an unknown target.",
                        "evidence_ids": ["evidence:missing"],
                        "rank": 1,
                        "recommendation_level": "strong_candidate",
                    }
                ]
            }
        )


class ValidProvider:
    name = "valid-provider"

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        return json.dumps(
            {
                "candidates": [
                    {
                        "candidate_type": "new_extension_component",
                        "proposed_extension_id": "extension:query_router",
                        "proposed_extension_name": "Query Router",
                        "proposed_extension_kind": "routing_orchestration",
                        "label": "Confirm Query Router as extension",
                        "rationale": "Router evidence is bounded and masked.",
                        "evidence_ids": ["evidence:router"],
                        "rank": 1,
                        "recommendation_level": "plausible_candidate",
                        "uncertainty_reason": "Static evidence only.",
                    }
                ]
            }
        )


def vector_store_packet() -> MappingEvidencePacket:
    return MappingEvidencePacket(
        project_id="project:demo",
        source_unmapped_id="unmapped:requirements_txt:line_1:dependency",
        source_file="requirements.txt",
        observed_kind="dependency_candidate",
        reason="Weak dependency signal.",
        evidence_ids=["evidence:chromadb"],
        rule_ids=["dependency_vector_store_client_chromadb"],
        masked_evidence_values=["chromadb"],
        dependency_signals=["chromadb"],
        available_slots=["vector_store", "retriever"],
    )


def router_packet() -> MappingEvidencePacket:
    return MappingEvidencePacket(
        project_id="project:demo",
        source_unmapped_id="unmapped:src_router_py:route",
        source_file="src/router.py",
        observed_kind="code_pattern",
        reason="Router-like code needs confirmation.",
        evidence_ids=["evidence:router"],
        rule_ids=["code_pattern_custom_router"],
        masked_evidence_values=["route_query"],
        call_like_signals=["QueryRouter.route"],
        available_slots=["app_api_or_orchestrator", "retriever"],
    )


def service(
    *,
    provider: MappingProposalProvider | None = None,
    manual_mapping_service: ManualMappingService | None = None,
) -> MappingProposalService:
    return MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        provider=provider,
        manual_mapping_service=manual_mapping_service,
    )


def test_deterministic_proposal_uses_rank_not_confidence() -> None:
    proposal = service().create_proposal(vector_store_packet())

    assert proposal.status == MappingProposalStatus.PENDING
    assert proposal.provider_name == "deterministic"
    assert len(proposal.candidates) >= 2
    assert proposal.candidates[0].candidate_type == (
        MappingCandidateType.EXISTING_SLOT
    )
    assert proposal.candidates[0].target_slot == "vector_store"
    assert proposal.candidates[0].rank == 1
    assert "confidence" not in json.dumps(proposal.model_dump(mode="json"))


def test_invalid_provider_output_retries_once_then_falls_back() -> None:
    provider = InvalidConfidenceProvider()

    proposal = service(provider=provider).create_proposal(
        vector_store_packet()
    )

    assert provider.calls == 2
    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason is not None
    assert "confidence" in proposal.provider_error_reason
    assert proposal.candidates[0].target_slot == "vector_store"


def test_hallucinated_provider_references_fallback() -> None:
    proposal = service(
        provider=HallucinatedReferenceProvider()
    ).create_proposal(vector_store_packet())

    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason is not None
    assert "unknown evidence" in proposal.provider_error_reason
    assert all(
        "evidence:missing" not in candidate.evidence_ids
        for candidate in proposal.candidates
    )


def test_valid_provider_candidates_are_saved() -> None:
    proposal = service(provider=ValidProvider()).create_proposal(
        router_packet()
    )

    assert proposal.provider_name == "valid-provider"
    assert proposal.candidates == [
        MappingCandidate(
            candidate_id=proposal.candidates[0].candidate_id,
            candidate_type=MappingCandidateType.NEW_EXTENSION,
            proposed_extension_id="extension:query_router",
            proposed_extension_name="Query Router",
            proposed_extension_kind="routing_orchestration",
            label="Confirm Query Router as extension",
            rationale="Router evidence is bounded and masked.",
            evidence_ids=["evidence:router"],
            rank=1,
            recommendation_level="plausible_candidate",
            uncertainty_reason="Static evidence only.",
        )
    ]


def test_accept_candidate_creates_manual_mapping_draft() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(vector_store_packet())
    candidate = proposal.candidates[0]

    result = proposal_service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.ACCEPT,
            candidate_id=candidate.candidate_id,
        ),
    )

    assert result.proposal.status == MappingProposalStatus.ACCEPTED
    assert result.manual_mapping is not None
    assert result.manual_mapping.project_id == "project:demo"
    assert result.manual_mapping.proposal_id == proposal.proposal_id
    assert result.manual_mapping.decision_source == "proposal_accept"
    assert result.manual_mapping.target_slot == "vector_store"
    assert manual_mapping_service.list_for_project("project:demo") == [
        result.manual_mapping
    ]


def test_reject_decision_does_not_create_manual_mapping() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(vector_store_packet())

    result = proposal_service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.REJECT,
            reason="Not part of the RAG path.",
        ),
    )

    assert result.proposal.status == MappingProposalStatus.REJECTED
    assert result.manual_mapping is None
    assert manual_mapping_service.list_for_project("project:demo") == []
