from __future__ import annotations

import pytest
from pydantic import ValidationError

from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.mapping import (
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
    MappingCandidate,
    MappingCandidateType,
)


def test_capability_candidate_is_confirmed_non_baseline_only() -> None:
    candidate = CapabilityCandidateComponent(
        id="capability-candidate:router",
        name="Query Router",
        observed_kind="routing_orchestration",
        evidence_ids=["evidence:router"],
        source_unmapped_component_id="unmapped:router",
    )

    assert candidate.status == "confirmed_non_baseline"


def test_manual_mapping_accepts_confirmed_non_baseline_candidate() -> None:
    mapping = ManualMappingCreate(
        project_id="project:demo",
        mapping_type=ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id="unmapped:router",
        source_file="src/router.py",
        observed_kind="routing_orchestration",
        evidence_ids=["evidence:router"],
        capability_candidate_id="capability-candidate:router",
        capability_candidate_name="Query Router",
        capability_candidate_kind="routing_orchestration",
    )

    assert (
        mapping.mapping_type
        is ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert mapping.capability_candidate_id == "capability-candidate:router"


@pytest.mark.parametrize(
    ("invalid_field", "invalid_value", "message"),
    [
        ("target_slot", "retriever", "must not include target_slot"),
        ("extension_id", "extension:router", "Extra inputs are not permitted"),
    ],
)
def test_manual_mapping_rejects_legacy_targets_for_non_baseline_candidate(
    invalid_field: str,
    invalid_value: str,
    message: str,
) -> None:
    payload = {
        "project_id": "project:demo",
        "mapping_type": "non_baseline_capability_candidate",
        "decision": "confirmed",
        "source_unmapped_id": "unmapped:router",
        "evidence_ids": ["evidence:router"],
        "capability_candidate_id": "capability-candidate:router",
        "capability_candidate_name": "Query Router",
        "capability_candidate_kind": "routing_orchestration",
        invalid_field: invalid_value,
    }

    with pytest.raises(ValidationError, match=message):
        ManualMappingCreate.model_validate(payload)


def test_mapping_candidate_requires_non_baseline_candidate_fields() -> None:
    candidate = MappingCandidate(
        candidate_type=MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE,
        proposed_capability_candidate_id="capability-candidate:reranker",
        proposed_capability_candidate_name="Reranker",
        proposed_capability_candidate_kind="reranker",
        label="Mark as non-baseline capability candidate",
        rationale="Reranker evidence is not canonical topology evidence.",
        evidence_ids=["evidence:reranker"],
        rank=1,
        recommendation_level="plausible_candidate",
    )

    assert (
        candidate.candidate_type
        is MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
