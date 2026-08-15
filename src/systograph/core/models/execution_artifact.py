from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from systograph.core.models.ai_system_map_v2 import EdgeObservationStatus
from systograph.core.models.artifact_scope import (
    PHASE2_P0_ARTIFACT_SET_VERSION,
    ArtifactSetVersion,
)


class ExecutionArtifactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactNode(ExecutionArtifactModel):
    node_id: str
    kind: str


class ArtifactEdge(ExecutionArtifactModel):
    edge_id: str
    source: str
    target: str
    relationship: str
    status: EdgeObservationStatus
    undetermined_reason: str | None = None
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_undetermined_reason(self) -> ArtifactEdge:
        if self.status == "undetermined" and not self.undetermined_reason:
            raise ValueError("undetermined artifact edge requires reason")
        return self


class ScopedExecutionArtifact(ExecutionArtifactModel):
    build_id: str
    scan_id: str
    environment_id: str
    artifact_set_version: ArtifactSetVersion = PHASE2_P0_ARTIFACT_SET_VERSION
    generated_from_build_id: str
    trace_kind: Literal["static_inferred"]
    runtime_verified: Literal[False]


class CallGraphArtifact(ScopedExecutionArtifact):
    schema_version: Literal["call-graph/v1"] = "call-graph/v1"
    nodes: tuple[ArtifactNode, ...] = ()
    edges: tuple[ArtifactEdge, ...] = ()


class DataflowHintsArtifact(ScopedExecutionArtifact):
    schema_version: Literal["dataflow-hints/v1"] = "dataflow-hints/v1"
    hints: tuple[ArtifactEdge, ...] = ()


class ExecutionPathsArtifact(ScopedExecutionArtifact):
    schema_version: Literal["execution-paths/v2"] = "execution-paths/v2"
    paths: tuple[ArtifactEdge, ...] = ()


class EvidenceTableRow(ExecutionArtifactModel):
    evidence_id: str
    artifact_type: str
    evidence_kind: str
    review_state: Literal[
        "confirmed",
        "rejected",
        "needs_confirmation",
        "not_required",
    ] = "not_required"
    relative_path: str | None = None
    rule_id: str | None = None
    summary: str | None = None


class EvidenceTableArtifact(ScopedExecutionArtifact):
    schema_version: Literal["evidence-table/v1"] = "evidence-table/v1"
    rows: tuple[EvidenceTableRow, ...] = ()
