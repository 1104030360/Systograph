from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from kai_mind.core.models.artifact_scope import (
    PHASE2_P0_ARTIFACT_SET_VERSION,
    ArtifactSetVersion,
)
from kai_mind.core.models.profile_signal import (
    ActivationState,
    MappingCompleteness,
    ProfileStatus,
)


class ReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadinessDimension(ReadinessModel):
    dimension_id: str
    status: ProfileStatus
    evidence_ids: tuple[str, ...] = ()
    reason: str | None = None


class GroundingReadinessSummary(ReadinessModel):
    applicability: Literal["applicable", "undetermined", "not_applicable"]
    status: ProfileStatus
    dimensions: tuple[ReadinessDimension, ...]
    evidence_ids: tuple[str, ...] = ()
    reason: str | None = None


class CapabilityReadinessSummary(ReadinessModel):
    profile_id: str
    status: ProfileStatus
    activation: ActivationState
    evidence_ids: tuple[str, ...] = ()


class ReadinessFinding(ReadinessModel):
    finding_id: str
    category: str
    status: ProfileStatus
    title: str
    reason: str
    evidence_ids: tuple[str, ...] = ()
    recommended_next_checks: tuple[str, ...] = ()


class ReadinessReport(ReadinessModel):
    schema_version: Literal["readiness-report/v1"] = "readiness-report/v1"
    source_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"]
    build_id: str
    scan_id: str
    environment_id: str
    artifact_set_version: ArtifactSetVersion = PHASE2_P0_ARTIFACT_SET_VERSION
    generated_from_build_id: str
    mapping_completeness: MappingCompleteness
    grounding: GroundingReadinessSummary
    capability_summaries: tuple[CapabilityReadinessSummary, ...]
    findings: tuple[ReadinessFinding, ...]
    recommended_next_checks: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    primary_map_type: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> ReadinessReport:
        if self.generated_from_build_id != self.build_id:
            raise ValueError("generated build id must match report build id")
        if any(
            not finding.evidence_ids and not finding.reason
            for finding in self.findings
        ):
            raise ValueError("readiness findings require evidence or reason")
        return self
