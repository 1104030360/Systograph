from __future__ import annotations

import pytest
from pydantic import ValidationError

from kai_mind.core.models.profile_signal import (
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
