"""Domain models for user-confirmed manual mapping decisions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
MAX_PROVIDER_ERROR_REASON_CHARS = 80


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
    def validate_candidate_shape(self) -> MappingCandidate:
        if self.candidate_type == MappingCandidateType.EXISTING_SLOT:
            if self.target_slot is None:
                raise ValueError("existing_slot_mapping requires target_slot")
            self._reject_extension_fields()
            return self

        if self.candidate_type == MappingCandidateType.NEW_EXTENSION:
            if (
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
            return self

        if (
            self.target_slot is not None
            or self.suggested_edges
            or self.proposed_extension_id is not None
            or self.proposed_extension_name is not None
            or self.proposed_extension_kind is not None
        ):
            raise ValueError(
                f"{self.candidate_type.value} must not include mapping target"
            )
        return self

    def _reject_extension_fields(self) -> None:
        if (
            self.proposed_extension_id is not None
            or self.proposed_extension_name is not None
            or self.proposed_extension_kind is not None
        ):
            raise ValueError(
                "existing_slot_mapping must not include extension fields"
            )


class MappingProviderCandidateBatch(MappingModel):
    candidates: list[MappingCandidate] = Field(
        default_factory=list,
        max_length=MAX_PROVIDER_CANDIDATES,
    )


class MappingProposal(MappingModel):
    proposal_id: str
    project_id: str
    source_unmapped_id: str
    status: MappingProposalStatus
    evidence_packet: MappingEvidencePacket
    candidates: list[MappingCandidate] = Field(
        max_length=MAX_PROVIDER_CANDIDATES,
    )
    provider_name: str
    provider_error_reason: str | None = Field(
        default=None,
        max_length=MAX_PROVIDER_ERROR_REASON_CHARS,
    )
    user_description: str | None = None
    available_actions: list[MappingProposalDecisionAction] = Field(
        default_factory=lambda: [
            MappingProposalDecisionAction.ACCEPT,
            MappingProposalDecisionAction.EDIT,
            MappingProposalDecisionAction.REJECT,
            MappingProposalDecisionAction.SKIP_FOR_NOW,
        ]
    )
    created_at: str
    updated_at: str


class MappingProposalDecisionRequest(MappingModel):
    decision: MappingProposalDecisionAction
    candidate_id: str | None = None
    edited_mapping: ManualMappingCreate | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_decision_payload(self) -> MappingProposalDecisionRequest:
        if self.decision == MappingProposalDecisionAction.ACCEPT:
            if self.candidate_id is None:
                raise ValueError("candidate_id is required for accept")
            if self.edited_mapping is not None:
                raise ValueError("accept must not include edited_mapping")
            return self

        if self.decision == MappingProposalDecisionAction.EDIT:
            if self.edited_mapping is None:
                raise ValueError("edited_mapping is required for edit")
            if self.candidate_id is not None:
                raise ValueError("edit must not include candidate_id")
            return self

        if self.candidate_id is not None or self.edited_mapping is not None:
            raise ValueError(
                f"{self.decision.value} must not include mapping payload"
            )
        return self


class MappingProposalDecisionResult(MappingModel):
    proposal: MappingProposal
    manual_mapping: ManualMapping | None = None
