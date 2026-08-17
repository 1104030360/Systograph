from __future__ import annotations

from systograph.core.models.mapping import (
    ManualMappingDecision,
    ManualMappingType,
    MappingCandidate,
    MappingCandidateType,
    MappingEvidencePacket,
    MappingProposal,
    MappingProposalDecisionAction,
    MappingProposalDecisionRequest,
    MappingProposalStatus,
)
from systograph.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingService,
)
from systograph.core.services.mapping_proposal_mapping_factory import (
    ProposalManualMappingFactory,
)


def router_proposal() -> MappingProposal:
    return MappingProposal(
        proposal_id="proposal:router",
        project_id="project:demo",
        source_unmapped_id="unmapped:src_router_py:route",
        status=MappingProposalStatus.PENDING,
        evidence_packet=MappingEvidencePacket(
            project_id="project:demo",
            source_unmapped_id="unmapped:src_router_py:route",
            source_file="src/router.py",
            observed_kind="code_pattern",
            reason="Router-like code needs confirmation.",
            evidence_ids=["evidence:router"],
            available_slots=["app_api_or_orchestrator", "retriever"],
        ),
        candidates=[
            MappingCandidate(
                candidate_id="candidate:needs-more-information",
                candidate_type=MappingCandidateType.NEEDS_MORE_INFORMATION,
                label="Ask for more mapping context",
                rationale="More bounded evidence would improve the mapping.",
                evidence_ids=["evidence:router"],
                rank=1,
                recommendation_level="needs_more_context",
            ),
            MappingCandidate(
                candidate_id="candidate:query-router",
                candidate_type=(
                    MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
                ),
                proposed_capability_candidate_id=(
                    "capability-candidate:query_router"
                ),
                proposed_capability_candidate_name="Query Router",
                proposed_capability_candidate_kind="routing_orchestration",
                label="Mark as non-baseline capability candidate",
                rationale="Router evidence is a capability signal.",
                evidence_ids=["evidence:router"],
                rank=2,
                recommendation_level="plausible_candidate",
            ),
            MappingCandidate(
                candidate_id="candidate:later-capability",
                candidate_type=(
                    MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
                ),
                proposed_capability_candidate_id=(
                    "capability-candidate:later"
                ),
                proposed_capability_candidate_name="Later Capability",
                proposed_capability_candidate_kind="later_kind",
                label="Later actionable candidate",
                rationale="This candidate must not replace the first one.",
                evidence_ids=["evidence:router"],
                rank=3,
                recommendation_level="plausible_candidate",
            ),
        ],
        provider_name="deterministic",
        created_at="2026-08-17T00:00:00Z",
        updated_at="2026-08-17T00:00:00Z",
    )


def test_create_audit_copies_capability_candidate_for_skip_for_now() -> None:
    repository = InMemoryManualMappingRepository()
    factory = ProposalManualMappingFactory(
        ManualMappingService(repository=repository)
    )

    mapping = factory.create_audit(
        router_proposal(),
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.SKIP_FOR_NOW,
            reason="Decide later.",
        ),
        decision=ManualMappingDecision.SKIP_FOR_NOW,
    )

    assert mapping.mapping_type == (
        ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert mapping.decision == ManualMappingDecision.SKIP_FOR_NOW
    assert mapping.proposal_id == "proposal:router"
    assert mapping.source_unmapped_id == "unmapped:src_router_py:route"
    assert mapping.observed_kind == "code_pattern"
    assert mapping.capability_candidate_id == (
        "capability-candidate:query_router"
    )
    assert mapping.capability_candidate_name == "Query Router"
    assert mapping.capability_candidate_kind == "routing_orchestration"
    assert mapping.decision_source == "proposal_skip_for_now"
    assert repository.list_for_project("project:demo") == [mapping]


def test_create_audit_copies_capability_candidate_for_reject() -> None:
    repository = InMemoryManualMappingRepository()
    factory = ProposalManualMappingFactory(
        ManualMappingService(repository=repository)
    )

    mapping = factory.create_audit(
        router_proposal(),
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.REJECT,
            reason="Not part of the RAG path.",
        ),
        decision=ManualMappingDecision.REJECTED,
    )

    assert mapping.mapping_type == (
        ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert mapping.decision == ManualMappingDecision.REJECTED
    assert mapping.proposal_id == "proposal:router"
    assert mapping.source_unmapped_id == "unmapped:src_router_py:route"
    assert mapping.observed_kind == "code_pattern"
    assert mapping.capability_candidate_id == (
        "capability-candidate:query_router"
    )
    assert mapping.capability_candidate_name == "Query Router"
    assert mapping.capability_candidate_kind == "routing_orchestration"
    assert mapping.decision_source == "proposal_reject"
    assert repository.list_for_project("project:demo") == [mapping]
