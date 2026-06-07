"""Domain models for user-confirmed manual mapping decisions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MappingModel(BaseModel):
    """Base model that rejects silent mapping contract drift."""

    model_config = ConfigDict(extra="forbid")


class ManualMappingType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NEW_EXTENSION = "new_extension_component"


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
    extension_id: str | None = None
    extension_name: str | None = None
    extension_kind: str | None = None
    extension_edges: list[dict[str, str]] = Field(default_factory=list)
    proposal_id: str | None = None
    decision_source: str = "manual"
    audit_metadata: dict[str, str] = Field(default_factory=dict)


class ManualMappingUpdate(MappingModel):
    decision: ManualMappingDecision | None = None
    reason: str | None = None
    target_slot: str | None = None
    component_name: str | None = None
    component_kind: str | None = None
    provider: str | None = None
    audit_metadata: dict[str, str] | None = None


class ManualMapping(ManualMappingCreate):
    mapping_id: str
    mapping_digest: str
    created_at: str
    updated_at: str
