from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CapabilityCandidateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CapabilityCandidateComponent(CapabilityCandidateModel):
    id: str
    name: str | None = None
    observed_kind: str
    status: Literal["confirmed_non_baseline"] = "confirmed_non_baseline"
    evidence_ids: list[str] = Field(default_factory=list)
    source_unmapped_component_id: str | None = None
    source_file: str | None = None
    proposal_id: str | None = None
    decision_source: str | None = None
