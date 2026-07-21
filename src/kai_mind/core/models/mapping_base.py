from __future__ import annotations

from enum import StrEnum
from typing import assert_never

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MappingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManualMappingType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NON_BASELINE_CAPABILITY_CANDIDATE = "non_baseline_capability_candidate"


class ManualMappingDecision(StrEnum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SKIP_FOR_NOW = "skip_for_now"
    NOT_APPLICABLE = "not_applicable"


class ManualMappingCreate(MappingModel):
    project_id: str
    mapping_type: ManualMappingType
    decision: ManualMappingDecision
    source_unmapped_id: str | None = None
    source_file: str | None = None
    observed_kind: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    target_slot: str | None = None
    component_name: str | None = None
    component_kind: str | None = None
    provider: str | None = None
    capability_candidate_id: str | None = None
    capability_candidate_name: str | None = None
    capability_candidate_kind: str | None = None
    proposal_id: str | None = None
    decision_source: str = "manual"
    audit_metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shape(self) -> ManualMappingCreate:
        candidate_fields_present = any(
            value is not None
            for value in (
                self.capability_candidate_id,
                self.capability_candidate_name,
                self.capability_candidate_kind,
            )
        )
        match self.mapping_type:
            case ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE:
                if self.target_slot is not None:
                    raise ValueError(
                        "non_baseline_capability_candidate must not include "
                        "target_slot"
                    )
                if not candidate_fields_present or (
                    self.capability_candidate_id is None
                    or self.capability_candidate_name is None
                    or self.capability_candidate_kind is None
                ):
                    raise ValueError(
                        "non-baseline capability mapping requires "
                        "candidate fields"
                    )
            case ManualMappingType.EXISTING_SLOT:
                if candidate_fields_present:
                    raise ValueError(
                        f"{self.mapping_type.value} must not include "
                        "candidate fields"
                    )
            case unreachable:
                assert_never(unreachable)
        return self


class ManualMappingUpdate(MappingModel):
    decision: ManualMappingDecision | None = None
    reason: str | None = None
    target_slot: str | None = None
    component_name: str | None = None
    component_kind: str | None = None
    provider: str | None = None
    capability_candidate_id: str | None = None
    capability_candidate_name: str | None = None
    capability_candidate_kind: str | None = None
    audit_metadata: dict[str, str] | None = None


class ManualMapping(ManualMappingCreate):
    mapping_id: str
    mapping_digest: str
    created_at: str
    updated_at: str
