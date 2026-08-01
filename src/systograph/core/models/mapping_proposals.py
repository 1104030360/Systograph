from __future__ import annotations

from enum import StrEnum
from typing import assert_never

from pydantic import Field, model_validator

from systograph.core.models.mapping_base import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    MappingModel,
)
from systograph.core.models.mapping_candidates import (
    MAX_PROVIDER_CANDIDATES,
    MAX_USER_DESCRIPTION_CHARS,
    MappingCandidate,
    MappingEvidencePacket,
)


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
    provider_error_reason: str | None = Field(default=None, max_length=80)
    user_description: str | None = Field(
        default=None,
        max_length=MAX_USER_DESCRIPTION_CHARS + len("...[truncated]"),
    )
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
    def validate_payload(self) -> MappingProposalDecisionRequest:
        match self.decision:
            case MappingProposalDecisionAction.ACCEPT:
                if self.candidate_id is None:
                    raise ValueError("candidate_id is required for accept")
                if self.edited_mapping is not None:
                    raise ValueError("accept must not include edited_mapping")
            case MappingProposalDecisionAction.EDIT:
                if self.edited_mapping is None:
                    raise ValueError("edited_mapping is required for edit")
                if self.candidate_id is not None:
                    raise ValueError("edit must not include candidate_id")
            case (
                MappingProposalDecisionAction.REJECT
                | MappingProposalDecisionAction.SKIP_FOR_NOW
            ):
                if (
                    self.candidate_id is not None
                    or self.edited_mapping is not None
                ):
                    raise ValueError(
                        f"{self.decision.value} must not include "
                        "mapping payload"
                    )
            case unreachable:
                assert_never(unreachable)
        return self


class MappingProposalDecisionResult(MappingModel):
    proposal: MappingProposal
    manual_mapping: ManualMapping | None = None

    @model_validator(mode="after")
    def validate_result(self) -> MappingProposalDecisionResult:
        match self.proposal.status:
            case MappingProposalStatus.ACCEPTED | MappingProposalStatus.EDITED:
                if self.manual_mapping is None:
                    raise ValueError(
                        f"{self.proposal.status.value} requires manual_mapping"
                    )
            case MappingProposalStatus.PENDING:
                if self.manual_mapping is not None:
                    raise ValueError(
                        "pending proposal must not include manual_mapping"
                    )
            case MappingProposalStatus.REJECTED:
                if (
                    self.manual_mapping is None
                    or self.manual_mapping.decision
                    != ManualMappingDecision.REJECTED
                ):
                    raise ValueError(
                        "rejected requires rejected manual_mapping"
                    )
            case MappingProposalStatus.SKIPPED:
                if (
                    self.manual_mapping is None
                    or self.manual_mapping.decision
                    != ManualMappingDecision.SKIP_FOR_NOW
                ):
                    raise ValueError(
                        "skipped requires skip_for_now manual_mapping"
                    )
            case unreachable:
                assert_never(unreachable)
        return self
