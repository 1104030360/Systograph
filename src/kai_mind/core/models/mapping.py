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


class MappingCandidateType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NEW_EXTENSION = "new_extension_component"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    SKIP_FOR_NOW = "skip_for_now"


class MappingProposalStatus(StrEnum):
    PENDING = "pending_user_confirmation"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class MappingProposalDecisionAction(StrEnum):
    ACCEPT = "accept"
    EDIT = "edit"
    REJECT = "reject"
    SKIP_FOR_NOW = "skip_for_now"


class SuggestedMappingEdge(MappingModel):
    source_ref: str
    target_ref: str
    relationship: str


class MappingEvidencePacket(MappingModel):
    project_id: str
    source_unmapped_id: str
    source_file: str | None = None
    observed_kind: str
    reason: str
    user_description: str | None = None
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
    candidate_id: str | None = None
    candidate_type: MappingCandidateType
    target_slot: str | None = None
    component_name: str | None = None
    component_kind: str | None = None
    provider: str | None = None
    proposed_extension_id: str | None = None
    proposed_extension_name: str | None = None
    proposed_extension_kind: str | None = None
    label: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    rank: int = Field(ge=1)
    recommendation_level: str
    uncertainty_reason: str | None = None
    suggested_edges: list[SuggestedMappingEdge] = Field(default_factory=list)
    flow_hint: str | None = None


class MappingProviderCandidateBatch(MappingModel):
    candidates: list[MappingCandidate] = Field(default_factory=list)


class MappingProposal(MappingModel):
    proposal_id: str
    project_id: str
    source_unmapped_id: str
    status: MappingProposalStatus
    evidence_packet: MappingEvidencePacket
    candidates: list[MappingCandidate]
    provider_name: str
    provider_error_reason: str | None = None
    user_description: str | None = None
    available_actions: list[str] = Field(
        default_factory=lambda: [
            "accept",
            "edit",
            "reject",
            "skip_for_now",
        ]
    )
    created_at: str
    updated_at: str


class MappingProposalDecisionRequest(MappingModel):
    decision: MappingProposalDecisionAction
    candidate_id: str | None = None
    edited_mapping: ManualMappingCreate | None = None
    reason: str | None = None


class MappingProposalDecisionResult(MappingModel):
    proposal: MappingProposal
    manual_mapping: ManualMapping | None = None
