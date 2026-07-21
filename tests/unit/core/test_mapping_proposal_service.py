from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from kai_mind.core.models.mapping import (
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
    MappingCandidate,
    MappingCandidateType,
    MappingEvidencePacket,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
    MappingProposalDecisionResult,
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


class ValidNonBaselineProvider:
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
                        "candidate_type": (
                            "non_baseline_capability_candidate"
                        ),
                        "proposed_capability_candidate_id": (
                            "capability-candidate:query_router"
                        ),
                        "proposed_capability_candidate_name": "Query Router",
                        "proposed_capability_candidate_kind": (
                            "routing_orchestration"
                        ),
                        "label": "Confirm Query Router as non-baseline",
                        "rationale": "Router evidence is bounded and masked.",
                        "evidence_ids": ["evidence:router"],
                        "rank": 1,
                        "recommendation_level": "plausible_candidate",
                        "uncertainty_reason": "Static evidence only.",
                    }
                ]
            }
        )


class NewExtensionToConfirmedComponentProvider:
    name = "confirmed-component-edge-provider"

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
                        "suggested_edges": [
                            {
                                "source_ref": "component:retriever:retriever",
                                "target_ref": "extension:query_router",
                                "relationship": "routes_to",
                            }
                        ],
                    }
                ]
            }
        )


class SecretLeakingProvider:
    name = "secret-leaking-provider"

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
                        "target_slot": "vector_store",
                        "label": "Map leaked key",
                        "rationale": "Use sk-live-secret-value here.",
                        "evidence_ids": ["evidence:chromadb"],
                        "rank": 1,
                        "recommendation_level": "strong_candidate",
                    }
                ]
            }
        )


class FieldSecretLeakingProvider:
    name = "field-secret-leaking-provider"

    def __init__(self, field_name: str) -> None:
        self._field_name = field_name

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        candidate: dict[str, object] = {
            "candidate_type": "existing_slot_mapping",
            "target_slot": "vector_store",
            "label": "Map vector store",
            "rationale": "The dependency is chromadb.",
            "evidence_ids": ["evidence:chromadb"],
            "rank": 1,
            "recommendation_level": "strong_candidate",
        }
        if self._field_name == "suggested_edges":
            candidate = {
                "candidate_type": "existing_slot_mapping",
                "target_slot": "vector_store",
                "label": "Map vector store",
                "rationale": "The dependency is chromadb.",
                "evidence_ids": ["evidence:chromadb"],
                "rank": 1,
                "recommendation_level": "strong_candidate",
                "suggested_edges": [
                    {
                        "source_ref": "retriever",
                        "target_ref": "vector_store",
                        "relationship": "sk-live-secret-value",
                    }
                ],
            }
            return json.dumps({"candidates": [candidate]})
        candidate[self._field_name] = "sk-live-secret-value"
        return json.dumps({"candidates": [candidate]})


class LongOutputProvider:
    name = "long-output-provider"

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
                        "target_slot": "vector_store",
                        "label": "x" * 1000,
                        "rationale": "The dependency is chromadb.",
                        "evidence_ids": ["evidence:chromadb"],
                        "rank": 1,
                        "recommendation_level": "strong_candidate",
                    }
                ]
            }
        )


class UnexpectedBugProvider:
    name = "unexpected-bug-provider"

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        raise RuntimeError("provider bug with sk-live-secret-value")


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
        confirmed_component_ids=["component:retriever:retriever"],
    )


def reranker_packet() -> MappingEvidencePacket:
    return MappingEvidencePacket(
        project_id="project:demo",
        source_unmapped_id="unmapped:src_reranker_py:reranker",
        source_file="src/reranker.py",
        observed_kind="reranker_candidate",
        reason="Detected reranker evidence.",
        evidence_ids=["evidence:reranker"],
        rule_ids=["code_pattern_reranker"],
        masked_evidence_values=["rerank"],
        available_slots=["retriever", "vector_store", "llm"],
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


def test_reranker_proposal_uses_non_baseline_capability_candidate() -> None:
    proposal = service().create_proposal(reranker_packet())

    candidate = proposal.candidates[0]
    assert candidate.candidate_type == (
        MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert candidate.proposed_capability_candidate_kind == "reranker"


def test_invalid_provider_output_retries_once_then_falls_back() -> None:
    provider = InvalidConfidenceProvider()

    proposal = service(provider=provider).create_proposal(
        vector_store_packet()
    )

    assert provider.calls == 2
    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason == "provider_invalid_output"
    assert proposal.candidates[0].target_slot == "vector_store"


def test_hallucinated_provider_references_fallback() -> None:
    proposal = service(
        provider=HallucinatedReferenceProvider()
    ).create_proposal(vector_store_packet())

    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason == "provider_invalid_output"
    assert all(
        "evidence:missing" not in candidate.evidence_ids
        for candidate in proposal.candidates
    )


def test_provider_output_with_unmasked_secret_falls_back_safely() -> None:
    proposal = service(provider=SecretLeakingProvider()).create_proposal(
        vector_store_packet()
    )

    serialized = json.dumps(proposal.model_dump(mode="json"))
    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason == "provider_invalid_output"
    assert "sk-live-secret-value" not in serialized


@pytest.mark.parametrize(
    "field_name,packet_factory",
    [
        ("label", vector_store_packet),
        ("component_name", vector_store_packet),
        ("provider", vector_store_packet),
        ("flow_hint", vector_store_packet),
        ("suggested_edges", vector_store_packet),
    ],
)
def test_provider_output_secret_fields_are_rejected(
    field_name: str,
    packet_factory: Callable[[], MappingEvidencePacket],
) -> None:
    proposal = service(
        provider=FieldSecretLeakingProvider(field_name)
    ).create_proposal(packet_factory())

    serialized = json.dumps(proposal.model_dump(mode="json"))
    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason == "provider_invalid_output"
    assert "sk-live-secret-value" not in serialized


def test_provider_output_bounded_fields_are_enforced() -> None:
    proposal = service(provider=LongOutputProvider()).create_proposal(
        vector_store_packet()
    )

    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason == "provider_invalid_output"
    assert proposal.candidates[0].target_slot == "vector_store"


def test_duplicate_pending_proposal_for_same_source_returns_existing() -> None:
    proposal_service = service()
    first = proposal_service.create_proposal(vector_store_packet())
    second = proposal_service.create_proposal(vector_store_packet())

    assert second.proposal_id == first.proposal_id
    assert proposal_service.list_for_project("project:demo") == [first]


def test_unexpected_provider_bug_is_not_silently_fallback() -> None:
    with pytest.raises(RuntimeError, match="provider bug"):
        service(provider=UnexpectedBugProvider()).create_proposal(
            vector_store_packet()
        )


def test_valid_provider_candidates_are_saved() -> None:
    proposal = service(provider=ValidNonBaselineProvider()).create_proposal(
        router_packet()
    )

    assert proposal.provider_name == "valid-provider"
    assert proposal.candidates == [
        MappingCandidate(
            candidate_id=proposal.candidates[0].candidate_id,
            candidate_type=(
                MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
            ),
            proposed_capability_candidate_id=(
                "capability-candidate:query_router"
            ),
            proposed_capability_candidate_name="Query Router",
            proposed_capability_candidate_kind="routing_orchestration",
            label="Confirm Query Router as non-baseline",
            rationale="Router evidence is bounded and masked.",
            evidence_ids=["evidence:router"],
            rank=1,
            recommendation_level="plausible_candidate",
            uncertainty_reason="Static evidence only.",
        )
    ]


def test_mapping_candidate_rejects_invalid_tagged_union_shape() -> None:
    with pytest.raises(ValidationError):
        MappingCandidate(
            candidate_type=MappingCandidateType.NEEDS_MORE_INFORMATION,
            target_slot="vector_store",
            label="Invalid needs-more-info candidate",
            rationale="This candidate should not target a slot.",
            evidence_ids=["evidence:chromadb"],
            rank=1,
            recommendation_level="needs_more_context",
        )


def test_provider_candidate_edges_must_be_persistable() -> None:
    proposal = service(
        provider=NewExtensionToConfirmedComponentProvider()
    ).create_proposal(router_packet())

    assert proposal.provider_name == "deterministic"
    assert proposal.provider_error_reason == "provider_invalid_output"
    assert all(
        not candidate.suggested_edges for candidate in proposal.candidates
    )


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


def test_accepting_nonbaseline_candidate_creates_manual_mapping() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(reranker_packet())

    result = proposal_service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.ACCEPT,
            candidate_id=proposal.candidates[0].candidate_id,
        ),
    )

    assert result.manual_mapping is not None
    assert result.manual_mapping.mapping_type == (
        ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert result.manual_mapping.capability_candidate_kind == "reranker"


def test_edit_decision_creates_manual_mapping_draft() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(vector_store_packet())
    edited_mapping = ManualMappingCreate(
        project_id="project:demo",
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id=proposal.source_unmapped_id,
        evidence_ids=["evidence:chromadb"],
        target_slot="vector_store",
        component_name="Edited Chroma",
        component_kind="vector_db",
    )

    result = proposal_service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.EDIT,
            edited_mapping=edited_mapping,
        ),
    )

    assert result.proposal.status == MappingProposalStatus.EDITED
    assert result.manual_mapping is not None
    assert result.manual_mapping.decision_source == "proposal_edit"
    assert result.manual_mapping.component_name == "Edited Chroma"


def test_edit_decision_overwrites_client_identity_fields() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(vector_store_packet())
    edited_mapping = ManualMappingCreate(
        project_id="project:evil",
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id="unmapped:evil",
        source_file="evil.py",
        observed_kind="evil_kind",
        evidence_ids=list(proposal.evidence_packet.evidence_ids),
        target_slot="vector_store",
        component_name="Edited Chroma",
        component_kind="vector_db",
    )

    result = proposal_service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.EDIT,
            edited_mapping=edited_mapping,
        ),
    )

    assert result.manual_mapping is not None
    assert result.manual_mapping.project_id == proposal.project_id
    assert result.manual_mapping.source_unmapped_id == (
        proposal.source_unmapped_id
    )
    assert result.manual_mapping.source_file == (
        proposal.evidence_packet.source_file
    )
    assert result.manual_mapping.observed_kind == (
        proposal.evidence_packet.observed_kind
    )


def test_edit_decision_rejects_unknown_evidence() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(vector_store_packet())
    edited_mapping = ManualMappingCreate(
        project_id=proposal.project_id,
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id=proposal.source_unmapped_id,
        evidence_ids=["evidence:evil"],
        target_slot="vector_store",
        component_name="Edited Chroma",
        component_kind="vector_db",
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        proposal_service.decide(
            proposal.proposal_id,
            MappingProposalDecisionRequest(
                decision=MappingProposalDecisionAction.EDIT,
                edited_mapping=edited_mapping,
            ),
        )


def test_skip_decision_creates_durable_audit_mapping() -> None:
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
            decision=MappingProposalDecisionAction.SKIP_FOR_NOW,
            reason="Later.",
        ),
    )

    assert result.proposal.status == MappingProposalStatus.SKIPPED
    assert result.manual_mapping is not None
    assert result.manual_mapping.decision == ManualMappingDecision.SKIP_FOR_NOW
    assert result.manual_mapping.reason == "Later."
    assert result.manual_mapping.audit_metadata["actor_surface"] == (
        "mapping_proposal"
    )
    assert result.manual_mapping.audit_metadata["acted_at"]
    assert manual_mapping_service.list_for_project("project:demo") == [
        result.manual_mapping
    ]


def test_unknown_candidate_decision_is_rejected() -> None:
    proposal_service = service(
        manual_mapping_service=ManualMappingService(
            repository=InMemoryManualMappingRepository(),
            allowed_slots={"vector_store"},
        ),
    )
    proposal = proposal_service.create_proposal(vector_store_packet())

    with pytest.raises(ValueError, match="Unknown candidate_id"):
        proposal_service.decide(
            proposal.proposal_id,
            MappingProposalDecisionRequest(
                decision=MappingProposalDecisionAction.ACCEPT,
                candidate_id="candidate:missing",
            ),
        )


def test_decision_request_rejects_conflicting_payloads() -> None:
    edited_mapping = ManualMappingCreate(
        project_id="project:demo",
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id="unmapped:demo",
        evidence_ids=["evidence:chromadb"],
        target_slot="vector_store",
        component_name="Edited Chroma",
        component_kind="vector_db",
    )

    with pytest.raises(ValidationError):
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.REJECT,
            candidate_id="candidate:1",
        )
    with pytest.raises(ValidationError):
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.ACCEPT,
            candidate_id="candidate:1",
            edited_mapping=edited_mapping,
        )
    with pytest.raises(ValidationError):
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.EDIT,
            candidate_id="candidate:1",
            edited_mapping=edited_mapping,
        )


def test_decision_requires_pending_proposal_status() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    proposal_service = service(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(vector_store_packet())
    candidate = proposal.candidates[0]
    proposal_service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.ACCEPT,
            candidate_id=candidate.candidate_id,
        ),
    )

    try:
        proposal_service.decide(
            proposal.proposal_id,
            MappingProposalDecisionRequest(
                decision=MappingProposalDecisionAction.REJECT,
                reason="late retry",
            ),
        )
    except ValueError as exc:
        assert "Proposal is not pending" in str(exc)
    else:
        raise AssertionError("expected non-pending proposal decision to fail")

    assert len(manual_mapping_service.list_for_project("project:demo")) == 1


def test_second_pending_accept_blocked_by_confirmed_mapping() -> None:
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
    )
    first_service = MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        manual_mapping_service=manual_mapping_service,
    )
    second_service = MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        manual_mapping_service=manual_mapping_service,
    )
    first = first_service.create_proposal(vector_store_packet())
    second = second_service.create_proposal(vector_store_packet())
    candidate = first.candidates[0]

    first_service.decide(
        first.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.ACCEPT,
            candidate_id=candidate.candidate_id,
        ),
    )

    with pytest.raises(ValueError, match="already has confirmed mapping"):
        second_service.decide(
            second.proposal_id,
            MappingProposalDecisionRequest(
                decision=MappingProposalDecisionAction.ACCEPT,
                candidate_id=second.candidates[0].candidate_id,
            ),
        )

    assert len(manual_mapping_service.list_for_project("project:demo")) == 1


def test_reject_decision_creates_durable_audit_mapping() -> None:
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
    assert result.manual_mapping is not None
    assert result.manual_mapping.decision == ManualMappingDecision.REJECTED
    assert result.manual_mapping.reason == "Not part of the RAG path."
    assert result.manual_mapping.proposal_id == proposal.proposal_id
    assert result.manual_mapping.audit_metadata["actor_surface"] == (
        "mapping_proposal"
    )
    assert manual_mapping_service.list_for_project("project:demo") == [
        result.manual_mapping
    ]


def test_decision_result_rejects_accepted_without_manual_mapping() -> None:
    proposal = service().create_proposal(vector_store_packet())

    with pytest.raises(ValidationError):
        MappingProposalDecisionResult(
            proposal=proposal.model_copy(
                update={"status": MappingProposalStatus.ACCEPTED}
            ),
            manual_mapping=None,
        )
