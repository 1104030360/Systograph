from __future__ import annotations

import pytest
from pydantic import ValidationError

from kai_mind.core.models.profile_signal import (
    ActivationState,
    MappingCompleteness,
    ProfileFinding,
    ReferenceCapabilityAssessment,
)


def test_detected_reference_assessment_requires_direct_evidence() -> None:
    assessment = ReferenceCapabilityAssessment(
        reference_node_id="reranker",
        plane_id="evidence",
        status="detected",
        activation="enabled",
        evidence_ids=("evidence:reranker",),
        direct_evidence_ids=("evidence:reranker",),
        build_id="build:test",
        scan_id="scan:test",
        environment_id="environment:default-static",
    )

    assert assessment.status == "detected"


def test_detected_reference_assessment_rejects_indirect_only_evidence() -> (
    None
):
    with pytest.raises(ValidationError, match="direct evidence"):
        ReferenceCapabilityAssessment(
            reference_node_id="reranker",
            plane_id="evidence",
            status="detected",
            activation="unknown",
            evidence_ids=("evidence:reranker",),
            indirect_evidence_ids=("evidence:reranker",),
            build_id="build:test",
            scan_id="scan:test",
            environment_id="environment:default-static",
        )


def test_profile_finding_rejects_confidence_and_shallow_detected_state() -> (
    None
):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProfileFinding.model_validate(
            {
                "profile_id": "reranking",
                "label": "Reranking",
                "primary_axis": "retrieval_strategy",
                "implementation_depth_level": 2,
                "status": "detected",
                "evidence_ids": ("evidence:reranker",),
                "direct_evidence_ids": ("evidence:reranker",),
                "evidence_strength": "static_single_signal",
                "build_id": "build:test",
                "scan_id": "scan:test",
                "environment_id": "environment:default-static",
                "confidence": 0.8,
            }
        )


def test_not_detected_profile_requires_completed_coverage_gate() -> None:
    with pytest.raises(ValidationError, match="coverage gate"):
        ProfileFinding(
            profile_id="graph-retrieval",
            label="Graph Retrieval",
            primary_axis="knowledge_structure",
            implementation_depth_level=0,
            status="not_detected",
            activation="unknown",
            evidence_strength="not_detected",
            build_id="build:test",
            scan_id="scan:test",
            environment_id="environment:default-static",
        )


@pytest.mark.parametrize(
    "activation",
    [
        "enabled",
        "disabled",
        "conditional",
        "unknown",
        "conflicted",
        "not_applicable",
    ],
)
def test_activation_state_does_not_change_profile_status(
    activation: ActivationState,
) -> None:
    # Given: one of the six activation states and an undetermined profile.
    finding = ProfileFinding(
        profile_id="reranking",
        label="Reranking",
        primary_axis="retrieval_strategy",
        implementation_depth_level=0,
        status="undetermined",
        activation=activation,
        evidence_strength="weak_or_ambiguous_signal",
        build_id="build:test",
        scan_id="scan:test",
        environment_id="environment:default-static",
    )

    # When / Then: activation is preserved without becoming a profile status.
    assert finding.activation == activation
    assert finding.status == "undetermined"


def test_mapping_completeness_rejects_external_weight_override() -> None:
    # Given: a complete status count with an attempted partial-weight override.
    payload = {
        "numerator": 26,
        "value": 0.5,
        "status_counts": {
            "detected": 0,
            "partial": 52,
            "undetermined": 0,
            "not_detected": 0,
            "conflicted": 0,
        },
        "weights": {"partial": 0.75},
    }

    # When / Then: the boundary rejects external scoring semantics.
    with pytest.raises(ValidationError, match="less than or equal to 0.5"):
        MappingCompleteness.model_validate(payload)
