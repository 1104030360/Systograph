from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from systograph.core.models.artifact_scope import (
    PHASE2_P0_ARTIFACT_SET_VERSION,
    ArtifactSetVersion,
)
from systograph.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)

ProfileStatus = Literal[
    "detected",
    "partial",
    "undetermined",
    "not_detected",
    "conflicted",
]
ActivationState = Literal[
    "enabled",
    "disabled",
    "conditional",
    "unknown",
    "conflicted",
    "not_applicable",
]
EvidenceStrength = Literal[
    "static_multiple_signals",
    "static_single_signal",
    "weak_or_ambiguous_signal",
    "not_detected",
]
ProfileAxis = Literal[
    "grounding",
    "agent_control",
    "tool_use",
    "memory",
    "workflow_orchestration",
    "retrieval_strategy",
    "knowledge_structure",
    "context_enrichment",
    "data_modality",
    "design_paradigm",
]
ImplementationDepthLevel = Literal[0, 1, 2, 3, 4]


class ProfileSignalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssessmentConflict(ProfileSignalModel):
    field: str
    evidence_ids: tuple[str, ...] = ()


class ReferenceCapabilityAssessment(ProfileSignalModel):
    reference_node_id: str
    plane_id: str
    status: ProfileStatus
    activation: ActivationState
    semantic_kind: Literal["reference_capability"] = "reference_capability"
    evidence_ids: tuple[str, ...] = ()
    direct_evidence_ids: tuple[str, ...] = ()
    indirect_evidence_ids: tuple[str, ...] = ()
    explicit_negative_evidence_ids: tuple[str, ...] = ()
    conflict_fields: tuple[AssessmentConflict, ...] = ()
    not_detected_coverage_gate_passed: bool = False
    related_component_ids: tuple[str, ...] = ()
    related_unmapped_component_ids: tuple[str, ...] = ()
    related_capability_candidate_component_ids: tuple[str, ...] = ()
    build_id: str
    scan_id: str
    environment_id: str

    @model_validator(mode="after")
    def validate_status(self) -> ReferenceCapabilityAssessment:
        if self.status == "detected" and not self.direct_evidence_ids:
            raise ValueError("detected assessments require direct evidence")
        if self.status == "not_detected" and not (
            self.not_detected_coverage_gate_passed
        ):
            raise ValueError("not_detected requires completed coverage gate")
        if self.status == "conflicted" and not self.conflict_fields:
            raise ValueError("conflicted requires field-specific conflicts")
        typed_evidence = set(
            self.direct_evidence_ids
            + self.indirect_evidence_ids
            + self.explicit_negative_evidence_ids
        )
        if not typed_evidence.issubset(set(self.evidence_ids)):
            raise ValueError("typed evidence must be listed in evidence_ids")
        return self


class ProfileFinding(ProfileSignalModel):
    profile_id: str
    label: str
    description: str | None = None
    status: ProfileStatus
    activation: ActivationState = "unknown"
    primary_axis: ProfileAxis
    secondary_axes: tuple[ProfileAxis, ...] = ()
    implementation_depth_level: ImplementationDepthLevel
    implementation_depth_reason: str | None = None
    evidence_ids: tuple[str, ...] = ()
    direct_evidence_ids: tuple[str, ...] = ()
    indirect_evidence_ids: tuple[str, ...] = ()
    explicit_negative_evidence_ids: tuple[str, ...] = ()
    conflict_fields: tuple[AssessmentConflict, ...] = ()
    detected_signals: tuple[str, ...] = ()
    missing_signals: tuple[str, ...] = ()
    coverage_detected: int = Field(default=0, ge=0)
    coverage_total: int = Field(default=0, ge=0)
    not_detected_coverage_gate_passed: bool = False
    evidence_strength: EvidenceStrength
    uncertainty: str | None = None
    related_component_ids: tuple[str, ...] = ()
    related_unmapped_component_ids: tuple[str, ...] = ()
    related_capability_candidate_component_ids: tuple[str, ...] = ()
    related_risk_hint_ids: tuple[str, ...] = ()
    recommended_next_checks: tuple[str, ...] = ()
    source: Literal["deterministic_static"] = "deterministic_static"
    build_id: str
    scan_id: str
    environment_id: str

    @model_validator(mode="after")
    def validate_status(self) -> ProfileFinding:
        if self.status == "detected":
            if not self.direct_evidence_ids:
                raise ValueError("detected profiles require direct evidence")
            if self.implementation_depth_level < 3:
                raise ValueError("detected profiles require depth >= 3")
        if self.status == "not_detected":
            if not self.not_detected_coverage_gate_passed:
                raise ValueError(
                    "not_detected requires completed coverage gate"
                )
            if self.implementation_depth_level != 0:
                raise ValueError("not_detected profiles require depth 0")
        if self.status == "conflicted" and not self.conflict_fields:
            raise ValueError("conflicted requires field-specific conflicts")
        if self.coverage_detected > self.coverage_total:
            raise ValueError("coverage_detected exceeds coverage_total")
        typed_evidence = set(
            self.direct_evidence_ids
            + self.indirect_evidence_ids
            + self.explicit_negative_evidence_ids
        )
        if not typed_evidence.issubset(set(self.evidence_ids)):
            raise ValueError("typed evidence must be listed in evidence_ids")
        return self


class MappingCompletenessWeights(ProfileSignalModel):
    detected: float = Field(default=1.0, ge=1.0, le=1.0)
    partial: float = Field(default=0.5, ge=0.5, le=0.5)
    undetermined: float = Field(default=0.0, ge=0.0, le=0.0)
    not_detected: float = Field(default=1.0, ge=1.0, le=1.0)
    conflicted: float = Field(default=0.0, ge=0.0, le=0.0)


class MappingStatusCounts(ProfileSignalModel):
    detected: int = Field(ge=0)
    partial: int = Field(ge=0)
    undetermined: int = Field(ge=0)
    not_detected: int = Field(ge=0)
    conflicted: int = Field(ge=0)


class MappingCompleteness(ProfileSignalModel):
    numerator: float = Field(ge=0, le=52)
    denominator: Literal[52] = 52
    value: float = Field(ge=0, le=1)
    status_counts: MappingStatusCounts
    weights: MappingCompletenessWeights = MappingCompletenessWeights()

    @model_validator(mode="after")
    def validate_calculation(self) -> MappingCompleteness:
        counts = self.status_counts
        if sum(counts.model_dump().values()) != self.denominator:
            raise ValueError("mapping completeness counts must total 52")
        expected = (
            counts.detected
            + counts.not_detected
            + counts.partial * self.weights.partial
        )
        if self.numerator != expected:
            raise ValueError("mapping completeness numerator is inconsistent")
        if self.value != self.numerator / self.denominator:
            raise ValueError("mapping completeness value is inconsistent")
        return self


class ProfileInferenceResult(ProfileSignalModel):
    schema_version: Literal["profile-signals/v1"] = "profile-signals/v1"
    source_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"]
    reference_catalog_version: Literal["1"] = "1"
    build_id: str
    scan_id: str
    environment_id: str
    artifact_set_version: ArtifactSetVersion = PHASE2_P0_ARTIFACT_SET_VERSION
    generated_from_build_id: str
    reference_capability_assessments: tuple[ReferenceCapabilityAssessment, ...]
    profiles: tuple[ProfileFinding, ...]
    capability_candidate_components: tuple[
        CapabilityCandidateComponent, ...
    ] = ()
    mapping_completeness: MappingCompleteness

    @model_validator(mode="after")
    def validate_complete_result(self) -> ProfileInferenceResult:
        if self.generated_from_build_id != self.build_id:
            raise ValueError("generated build id must match profile build id")
        if len(self.reference_capability_assessments) != 52:
            raise ValueError("profile result requires exactly 52 assessments")
        node_ids = {
            item.reference_node_id
            for item in self.reference_capability_assessments
        }
        if len(node_ids) != 52:
            raise ValueError("profile result assessment ids must be unique")
        if len(self.profiles) != 15:
            raise ValueError("profile result requires exactly 15 profiles")
        if len({item.profile_id for item in self.profiles}) != 15:
            raise ValueError("profile result profile ids must be unique")
        for item in self.reference_capability_assessments:
            if (
                item.build_id != self.build_id
                or item.scan_id != self.scan_id
                or item.environment_id != self.environment_id
            ):
                raise ValueError(
                    "profile result contains mixed assessment scope"
                )
        for profile in self.profiles:
            if (
                profile.build_id != self.build_id
                or profile.scan_id != self.scan_id
                or profile.environment_id != self.environment_id
            ):
                raise ValueError(
                    "profile result contains mixed assessment scope"
                )
        return self
