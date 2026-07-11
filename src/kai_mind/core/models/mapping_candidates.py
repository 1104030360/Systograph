from __future__ import annotations

from enum import StrEnum
from typing import assert_never

from pydantic import Field, model_validator

from kai_mind.core.models.mapping_base import MappingModel

MAX_MAPPING_REF_CHARS = 160
MAX_MAPPING_RELATIONSHIP_CHARS = 80
MAX_MAPPING_SLOT_CHARS = 80
MAX_COMPONENT_NAME_CHARS = 120
MAX_COMPONENT_KIND_CHARS = 80
MAX_PROVIDER_NAME_CHARS = 80
MAX_CANDIDATE_LABEL_CHARS = 160
MAX_CANDIDATE_RATIONALE_CHARS = 800
MAX_CANDIDATE_EVIDENCE_IDS = 12
MAX_RECOMMENDATION_LEVEL_CHARS = 80
MAX_UNCERTAINTY_REASON_CHARS = 400
MAX_SUGGESTED_EDGES = 8
MAX_FLOW_HINT_CHARS = 800
MAX_PROVIDER_CANDIDATES = 3
MAX_USER_DESCRIPTION_CHARS = 1000


class MappingCandidateType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NEW_EXTENSION = "new_extension_component"
    NON_BASELINE_CAPABILITY_CANDIDATE = "non_baseline_capability_candidate"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    SKIP_FOR_NOW = "skip_for_now"


class SuggestedMappingEdge(MappingModel):
    source_ref: str = Field(max_length=MAX_MAPPING_REF_CHARS)
    target_ref: str = Field(max_length=MAX_MAPPING_REF_CHARS)
    relationship: str = Field(max_length=MAX_MAPPING_RELATIONSHIP_CHARS)


class MappingEvidencePacket(MappingModel):
    project_id: str
    source_unmapped_id: str
    source_file: str | None = None
    observed_kind: str
    reason: str
    user_description: str | None = Field(
        default=None,
        max_length=MAX_USER_DESCRIPTION_CHARS + len("...[truncated]"),
    )
    evidence_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    line_ranges: list[str] = Field(default_factory=list)
    masked_evidence_values: list[str] = Field(default_factory=list)
    masked_snippets: list[str] = Field(default_factory=list)
    dependency_signals: list[str] = Field(default_factory=list)
    import_signals: list[str] = Field(default_factory=list)
    class_function_signals: list[str] = Field(default_factory=list)
    call_like_signals: list[str] = Field(default_factory=list)
    context_limits: dict[str, str | int | bool] = Field(default_factory=dict)
    available_slots: list[str] = Field(default_factory=list)
    available_extensions: list[str] = Field(default_factory=list)
    confirmed_component_ids: list[str] = Field(default_factory=list)


class MappingCandidate(MappingModel):
    candidate_id: str | None = Field(
        default=None,
        max_length=MAX_MAPPING_REF_CHARS,
    )
    candidate_type: MappingCandidateType
    target_slot: str | None = Field(
        default=None,
        max_length=MAX_MAPPING_SLOT_CHARS,
    )
    component_name: str | None = Field(
        default=None,
        max_length=MAX_COMPONENT_NAME_CHARS,
    )
    component_kind: str | None = Field(
        default=None,
        max_length=MAX_COMPONENT_KIND_CHARS,
    )
    provider: str | None = Field(
        default=None,
        max_length=MAX_PROVIDER_NAME_CHARS,
    )
    proposed_extension_id: str | None = Field(
        default=None,
        max_length=MAX_MAPPING_REF_CHARS,
    )
    proposed_extension_name: str | None = Field(
        default=None,
        max_length=MAX_COMPONENT_NAME_CHARS,
    )
    proposed_extension_kind: str | None = Field(
        default=None,
        max_length=MAX_COMPONENT_KIND_CHARS,
    )
    proposed_capability_candidate_id: str | None = Field(
        default=None,
        max_length=MAX_MAPPING_REF_CHARS,
    )
    proposed_capability_candidate_name: str | None = Field(
        default=None,
        max_length=MAX_COMPONENT_NAME_CHARS,
    )
    proposed_capability_candidate_kind: str | None = Field(
        default=None,
        max_length=MAX_COMPONENT_KIND_CHARS,
    )
    label: str = Field(max_length=MAX_CANDIDATE_LABEL_CHARS)
    rationale: str = Field(max_length=MAX_CANDIDATE_RATIONALE_CHARS)
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_CANDIDATE_EVIDENCE_IDS,
    )
    rank: int = Field(ge=1)
    recommendation_level: str = Field(
        max_length=MAX_RECOMMENDATION_LEVEL_CHARS,
    )
    uncertainty_reason: str | None = Field(
        default=None,
        max_length=MAX_UNCERTAINTY_REASON_CHARS,
    )
    suggested_edges: list[SuggestedMappingEdge] = Field(
        default_factory=list,
        max_length=MAX_SUGGESTED_EDGES,
    )
    flow_hint: str | None = Field(
        default=None,
        max_length=MAX_FLOW_HINT_CHARS,
    )

    @model_validator(mode="after")
    def validate_shape(self) -> MappingCandidate:
        extension_fields_present = any(
            value is not None
            for value in (
                self.proposed_extension_id,
                self.proposed_extension_name,
                self.proposed_extension_kind,
            )
        )
        capability_fields_present = any(
            value is not None
            for value in (
                self.proposed_capability_candidate_id,
                self.proposed_capability_candidate_name,
                self.proposed_capability_candidate_kind,
            )
        )
        match self.candidate_type:
            case MappingCandidateType.EXISTING_SLOT:
                if self.target_slot is None:
                    raise ValueError(
                        "existing_slot_mapping requires target_slot"
                    )
                if extension_fields_present:
                    raise ValueError(
                        "existing slot candidate cannot include "
                        "extension fields"
                    )
                if capability_fields_present:
                    raise ValueError(
                        "existing_slot_mapping must not include capability "
                        "candidate fields"
                    )
            case MappingCandidateType.NEW_EXTENSION:
                if not extension_fields_present or (
                    self.proposed_extension_id is None
                    or self.proposed_extension_name is None
                    or self.proposed_extension_kind is None
                ):
                    raise ValueError(
                        "new_extension_component requires extension fields"
                    )
                if self.target_slot is not None:
                    raise ValueError(
                        "new_extension_component must not include target_slot"
                    )
                if capability_fields_present:
                    raise ValueError(
                        "new_extension_component must not include capability "
                        "candidate fields"
                    )
            case MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE:
                if not capability_fields_present or (
                    self.proposed_capability_candidate_id is None
                    or self.proposed_capability_candidate_name is None
                    or self.proposed_capability_candidate_kind is None
                ):
                    raise ValueError(
                        "non-baseline capability candidate requires fields"
                    )
                if self.target_slot is not None:
                    raise ValueError(
                        "non_baseline_capability_candidate must not include "
                        "target_slot"
                    )
                if extension_fields_present:
                    raise ValueError(
                        "non_baseline_capability_candidate must not include "
                        "extension fields"
                    )
                if self.suggested_edges:
                    raise ValueError(
                        "non_baseline_capability_candidate must not include "
                        "suggested_edges"
                    )
            case (
                MappingCandidateType.NEEDS_MORE_INFORMATION
                | MappingCandidateType.SKIP_FOR_NOW
            ):
                if (
                    self.target_slot is not None
                    or extension_fields_present
                    or capability_fields_present
                    or self.suggested_edges
                ):
                    raise ValueError(
                        f"{self.candidate_type.value} must not include "
                        "mapping target"
                    )
            case unreachable:
                assert_never(unreachable)
        return self


class MappingProviderCandidateBatch(MappingModel):
    candidates: list[MappingCandidate] = Field(
        default_factory=list,
        max_length=MAX_PROVIDER_CANDIDATES,
    )
