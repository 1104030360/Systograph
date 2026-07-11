from __future__ import annotations

from collections.abc import Sequence

from kai_mind.core.models.profile_signal import (
    ActivationState,
    EvidenceStrength,
    ImplementationDepthLevel,
    ProfileStatus,
    ReferenceCapabilityAssessment,
)


def infer_profile_status(
    required: Sequence[ReferenceCapabilityAssessment],
    *,
    relationship_met: bool,
) -> tuple[ProfileStatus, ImplementationDepthLevel, str | None]:
    if any(item.status == "conflicted" for item in required):
        return (
            "conflicted",
            2,
            "Deterministic capability evidence conflicts by field.",
        )
    if all(
        item.status == "not_detected"
        and item.not_detected_coverage_gate_passed
        for item in required
    ):
        return (
            "not_detected",
            0,
            "Capability-specific coverage completed without "
            "positive evidence.",
        )
    if (
        all(item.status == "detected" for item in required)
        and relationship_met
    ):
        return "detected", 3, None
    if required[0].status in {"detected", "partial"}:
        depth: ImplementationDepthLevel = (
            2 if any(item.direct_evidence_ids for item in required) else 1
        )
        return (
            "partial",
            depth,
            "Required deterministic signals or wiring are incomplete.",
        )
    return (
        "undetermined",
        0,
        "Scanner coverage is insufficient to prove absence.",
    )


def evidence_strength(
    status: ProfileStatus,
    direct_evidence_ids: tuple[str, ...],
) -> EvidenceStrength:
    if status == "not_detected":
        return "not_detected"
    if len(direct_evidence_ids) > 1:
        return "static_multiple_signals"
    if direct_evidence_ids:
        return "static_single_signal"
    return "weak_or_ambiguous_signal"


def activation(
    assessments: Sequence[ReferenceCapabilityAssessment],
) -> ActivationState:
    states = {
        item.activation
        for item in assessments
        if item.activation not in {"unknown", "not_applicable"}
    }
    if not states:
        return "unknown"
    if "disabled" in states:
        return "disabled" if len(states) == 1 else "conflicted"
    if "conditional" in states:
        return "conditional"
    if len(states) > 1:
        return "conflicted"
    return next(iter(states))
