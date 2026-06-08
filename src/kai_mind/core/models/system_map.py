"""Pydantic models for the ai-system-map/v1 contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "ai-system-map/v1"
SCHEMA_ID = "https://kai-mind.local/schemas/ai-system-map.v1.schema.json"
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

SystemMapSchemaVersion = Literal["ai-system-map/v1"]
SystemType = Literal["rag"]
ClassificationMode = Literal["user_selected_or_default"]
ScanDepth = Literal["system", "component", "code_path"]
SlotStatus = Literal["detected", "missing", "not_configured", "not_applicable"]
EndpointType = Literal["local", "external"]
RiskTargetType = Literal[
    "component_instance", "endpoint", "component_slot", "evidence", "file"
]


class ContractModel(BaseModel):
    """Base model that forbids silent contract drift."""

    model_config = ConfigDict(extra="forbid")


class Classification(ContractModel):
    mode: ClassificationMode
    selected_template: Literal["rag-core-v1"]
    future_layer: str | None = None


class Project(ContractModel):
    name: str
    root_path: str | None = None
    root_path_redacted: str | None = None
    path_mode: str | None = None
    system_map_schema_version: SystemMapSchemaVersion | None = None


class ReferenceArchitecture(ContractModel):
    id: Literal["rag-core-v1"]
    version: str | None = None
    slots: list[str]
    flows: list[str]


class ComponentInstance(ContractModel):
    id: str
    slot: str
    kind: str
    name: str
    description: str | None = None
    provider: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ComponentSlot(ContractModel):
    slot: str
    required_for_rag: bool
    status: SlotStatus
    instances: list[ComponentInstance] = Field(default_factory=list)


class Evidence(ContractModel):
    id: str
    kind: str
    file: str | None = None
    path: str | None = None
    value: str | None = None
    rule_id: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    snippet: str | None = None


class Endpoint(ContractModel):
    id: str
    value: str
    endpoint_type: EndpointType
    method: str | None = None
    slot: str | None = None
    component_instance_id: str | None = None
    evidence_id: str


class Edge(ContractModel):
    id: str
    flow_id: str
    from_slot: str
    to_slot: str
    from_component_id: str | None = None
    to_component_id: str | None = None
    relationship: str
    evidence_ids: list[str] = Field(default_factory=list)


class Flow(ContractModel):
    id: str
    name: str | None = None
    flow_type: str | None = None
    edges: list[Edge] = Field(default_factory=list)


class RiskHint(ContractModel):
    id: str
    type: str
    target: str
    target_type: RiskTargetType
    evidence_id: str
    rule_id: str
    rationale: str
    uncertainty: str | None = None
    severity_hint: str | None = None


class DetailScanFinding(ContractModel):
    kind: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    best_effort: bool | None = None


class CodePathStep(ContractModel):
    file: str
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence_id: str | None = None
    best_effort: bool | None = None


class DetailScanResult(ContractModel):
    id: str
    target_type: str
    target: str
    scan_depth: ScanDepth
    status: str
    replay_depth: str | None = None
    findings: list[DetailScanFinding] = Field(default_factory=list)
    code_path: list[CodePathStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    best_effort: bool | None = None
    context_limits: dict[str, Any] = Field(default_factory=dict)


class QueryTraceEvent(ContractModel):
    id: str
    trace_id: str | None = None
    sequence_index: int
    timestamp: str
    replay_depth: str | None = None
    slot: str | None = None
    component_id: str | None = None
    edge_id: str | None = None
    input: Any | None = None
    output: Any | None = None
    latency_ms: int | float | None = None
    latency: str | None = None
    error: Any | None = None
    retrieved_chunks: Any | None = None


class ExtensionComponent(ContractModel):
    id: str
    name: str
    kind: str
    status: str
    confirmed_by_user: bool | None = None
    description: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class UnmappedComponent(ContractModel):
    id: str
    source_file: str | None = None
    observed_kind: str
    status: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class RecommendedNextCheck(ContractModel):
    id: str
    target_type: str
    target: str
    reason: str
    action: str


class ScanSummary(ContractModel):
    status: str
    files_scanned: int = 0
    files_skipped: int = 0
    detected_slots: int = 0
    missing_slots: int = 0
    not_configured_slots: int = 0
    unmapped_components: int = 0
    risk_hints: int = 0
    secret_masking_applied: bool = False


class RagSystemMap(ContractModel):
    schema_version: SystemMapSchemaVersion
    system_type: SystemType
    classification: Classification
    project: Project
    reference_architecture: ReferenceArchitecture
    scan_depth: ScanDepth
    scan_summary: ScanSummary | None = None
    components_by_slot: dict[str, ComponentSlot]
    evidence: list[Evidence]
    endpoints: list[Endpoint]
    flows: list[Flow]
    extensions: list[ExtensionComponent]
    unmapped_components: list[UnmappedComponent]
    detail_scans: list[DetailScanResult]
    risk_hints: list[RiskHint]
    recommended_next_checks: list[RecommendedNextCheck]
    query_trace_events: list[QueryTraceEvent]


def build_system_map_schema() -> dict[str, Any]:
    """Return the deterministic JSON Schema artifact for ai-system-map/v1."""

    schema = RagSystemMap.model_json_schema()
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = SCHEMA_ID
    return schema
