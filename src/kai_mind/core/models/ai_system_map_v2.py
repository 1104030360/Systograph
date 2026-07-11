"""Canonical and compatibility models for ai-system-map/v2."""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kai_mind.core.models.system_map import Evidence

# ---------------------------------------------------------------------------
# Shared literals
# ---------------------------------------------------------------------------

CompatibilitySchemaVersion = Literal["ai-system-map/v2"]
CompatibilitySystemType = Literal["ai_system"]
V2SchemaVersion = Literal["ai-system-map/v2"]
V2SystemType = Literal["ai_system"]

AssessmentStatus = Literal[
    "detected",
    "partial",
    "undetermined",
    "not_detected",
    "conflicted",
]
ActivationState = Literal[
    "enabled",
    "disabled",
    "conditional",
    "unknown",
    "conflicted",
    "not_applicable",
]
AssessmentEvidenceKind = Literal["direct", "indirect", "explicit_negative"]
DetectionStatus = Literal[
    "detected",
    "missing",
    "not_configured",
    "not_applicable",
    "confirmed",
    "partial",
    "undetermined",
]
EdgeObservationStatus = Literal["observed", "detected", "undetermined"]
EndpointTypeV2 = Literal["local", "external"]
RiskTargetTypeV2 = Literal["component", "endpoint", "evidence", "file"]
SemanticKind = Literal[
    "repo_component",
    "slot_placeholder",
    "legacy_extension",
    "reference_capability",
    "workflow_node",
]

CompatibilityActivation = ActivationState
CompatibilityComponentStatus = DetectionStatus
CompatibilityLayer = Literal[
    "input_intent",
    "control",
    "ingestion_indexing",
    "retrieval",
    "extension_subsystems",
    "evidence",
    "generation",
    "memory_state",
    "governance_observability",
    "deployment_topology",
    "undetermined",
]
CompatibilityComponentSemanticKind = Literal[
    "repo_component",
    "slot_placeholder",
    "legacy_extension",
]
CompatibilityEdgeStatus = Literal["observed"]
CompatibilityEndpointType = EndpointTypeV2
CompatibilityRiskTargetType = RiskTargetTypeV2
CompatibilityCandidateKind = Literal["legacy_extension"]

V2_SCHEMA_VERSION: Final[V2SchemaVersion] = "ai-system-map/v2"
V2_SYSTEM_TYPE: Final[V2SystemType] = "ai_system"
DEFAULT_ENVIRONMENT_ID: Final[str] = "environment:default-static"
REFERENCE_MAP_VERSION: Final[str] = "1"
REFERENCE_PLANE_COUNT: Final[int] = 10
REFERENCE_NODE_COUNT: Final[int] = 52
JSON_SCHEMA_DRAFT: Final[str] = "https://json-schema.org/draft/2020-12/schema"
V2_SCHEMA_ID: Final[str] = (
    "https://kai-mind.local/schemas/ai-system-map.v2.schema.json"
)


class V2ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CompatibilityContractModel(V2ContractModel):
    pass


# ---------------------------------------------------------------------------
# Compatibility view (Plan 00 adapter output)
# ---------------------------------------------------------------------------


class CompatibilityProject(CompatibilityContractModel):
    name: str
    root_path: str | None = None
    root_path_redacted: str | None = None
    path_mode: str | None = None


class GenericComponentMetadata(CompatibilityContractModel):
    legacy_slot: str | None = None
    source_component_id: str | None = None
    source_extension_id: str | None = None
    semantic_kind: CompatibilityComponentSemanticKind
    required_for_rag: bool | None = None
    source_status: str | None = None
    source_kind: str | None = None


class GenericComponent(CompatibilityContractModel):
    component_id: str
    display_name: str
    canonical_type: str
    layer: CompatibilityLayer
    status: CompatibilityComponentStatus
    activation: CompatibilityActivation
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: GenericComponentMetadata


class GenericEdgeMetadata(CompatibilityContractModel):
    source_edge_id: str
    flow_id: str
    from_slot: str
    to_slot: str


class GenericEdge(CompatibilityContractModel):
    edge_id: str
    source: str
    target: str
    relationship: str
    status: CompatibilityEdgeStatus
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: GenericEdgeMetadata


class GenericEndpointMetadata(CompatibilityContractModel):
    source_endpoint_id: str
    legacy_slot: str | None = None
    source_component_id: str | None = None


class GenericEndpoint(CompatibilityContractModel):
    endpoint_id: str
    value: str
    endpoint_type: CompatibilityEndpointType
    method: str | None = None
    component_id: str | None = None
    evidence_id: str
    metadata: GenericEndpointMetadata


class GenericRiskHintMetadata(CompatibilityContractModel):
    source_risk_id: str
    source_target: str
    source_target_type: str


class GenericRiskHint(CompatibilityContractModel):
    risk_id: str
    type: str
    target: str
    target_type: CompatibilityRiskTargetType
    evidence_id: str
    rule_id: str
    rationale: str
    uncertainty: str | None = None
    severity_hint: str | None = None
    metadata: GenericRiskHintMetadata


class GenericUnmappedFact(CompatibilityContractModel):
    unmapped_fact_id: str
    observed_kind: str
    status: str
    reason: str
    source_file: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class GenericCandidateFactMetadata(CompatibilityContractModel):
    source_extension_id: str
    confirmed_by_user: bool | None = None
    source_status: str


class GenericCandidateFact(CompatibilityContractModel):
    candidate_fact_id: str
    candidate_kind: CompatibilityCandidateKind
    display_name: str
    source_component_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: GenericCandidateFactMetadata


class AiSystemMapV2CompatibilityView(CompatibilityContractModel):
    schema_version: CompatibilitySchemaVersion = V2_SCHEMA_VERSION
    system_type: CompatibilitySystemType = V2_SYSTEM_TYPE
    source_schema_version: Literal["ai-system-map/v1"]
    project: CompatibilityProject
    components: list[GenericComponent] = Field(default_factory=list)
    edges: list[GenericEdge] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    endpoints: list[GenericEndpoint] = Field(default_factory=list)
    risk_hints: list[GenericRiskHint] = Field(default_factory=list)
    unmapped_facts: list[GenericUnmappedFact] = Field(default_factory=list)
    candidate_facts: list[GenericCandidateFact] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical ai-system-map/v2
# ---------------------------------------------------------------------------


class CanonicalProject(V2ContractModel):
    project_id: str | None = None
    name: str
    root_path: str | None = None
    root_path_redacted: str | None = None
    path_mode: str | None = None


class CanonicalEvidenceLocation(V2ContractModel):
    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    json_pointer: str | None = None
    config_key: str | None = None


class CanonicalEvidence(V2ContractModel):
    evidence_id: str
    artifact_type: str
    evidence_kind: AssessmentEvidenceKind
    location: CanonicalEvidenceLocation
    extract_summary: str | None = None
    rule_id: str | None = None


class CanonicalComponent(V2ContractModel):
    component_id: str
    display_name: str
    canonical_type: str
    layer: CompatibilityLayer
    status: DetectionStatus
    activation: ActivationState
    evidence_ids: list[str] = Field(default_factory=list)
    framework: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalEdge(V2ContractModel):
    edge_id: str
    source: str
    target: str
    relationship: str
    status: EdgeObservationStatus
    evidence_ids: list[str] = Field(default_factory=list)
    undetermined_reason: str | None = None


class CanonicalEndpoint(V2ContractModel):
    endpoint_id: str
    value: str
    endpoint_type: EndpointTypeV2
    method: str | None = None
    component_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class CanonicalRiskHint(V2ContractModel):
    risk_id: str
    type: str
    target: str
    target_type: RiskTargetTypeV2
    evidence_id: str
    rule_id: str
    rationale: str
    uncertainty: str | None = None
    severity_hint: str | None = None


class CanonicalUnmappedComponent(V2ContractModel):
    unmapped_id: str
    observed_kind: str
    status: str
    reason: str
    source_file: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class CanonicalCandidateFactMetadata(V2ContractModel):
    source_extension_id: str
    confirmed_by_user: bool | None = None
    source_status: str


class CanonicalCandidateFact(V2ContractModel):
    candidate_fact_id: str
    candidate_kind: CompatibilityCandidateKind
    display_name: str
    source_component_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: CanonicalCandidateFactMetadata


class AiSystemMapV2(V2ContractModel):
    # Artifact badges must be explicit in JSON; defaults would omit them from
    # generated JSON Schema `required` and let schema-only gates accept maps
    # that CanonicalMapLoader cannot load.
    schema_version: V2SchemaVersion
    system_type: V2SystemType
    scan_id: str | None = None
    build_id: str | None = None
    environment_id: str = DEFAULT_ENVIRONMENT_ID
    generated_from_build_id: str | None = None
    source_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"] | (
        None
    ) = None
    migration_warnings: list[str] = Field(default_factory=list)
    project: CanonicalProject
    components: list[CanonicalComponent] = Field(default_factory=list)
    edges: list[CanonicalEdge] = Field(default_factory=list)
    evidence: list[CanonicalEvidence] = Field(default_factory=list)
    endpoints: list[CanonicalEndpoint] = Field(default_factory=list)
    risk_hints: list[CanonicalRiskHint] = Field(default_factory=list)
    unmapped_components: list[CanonicalUnmappedComponent] = Field(
        default_factory=list
    )
    candidate_facts: list[CanonicalCandidateFact] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Assessment / reference map / derived projections
# ---------------------------------------------------------------------------


class FieldConflict(V2ContractModel):
    field_name: str
    evidence_ids_a: list[str] = Field(default_factory=list)
    evidence_ids_b: list[str] = Field(default_factory=list)


class CapabilityAssessment(V2ContractModel):
    reference_node_id: str
    plane_id: str
    status: AssessmentStatus
    activation: ActivationState
    semantic_kind: SemanticKind = "reference_capability"
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_kinds: dict[str, AssessmentEvidenceKind] = Field(
        default_factory=dict
    )
    conflict_fields: list[FieldConflict] = Field(default_factory=list)
    not_detected_coverage_gate_passed: bool | None = None
    build_id: str
    scan_id: str
    environment_id: str = DEFAULT_ENVIRONMENT_ID


class GroundingReadiness(V2ContractModel):
    """Derived projection for readiness findings — not canonical map truth."""

    status: AssessmentStatus
    missing_signals: list[str] = Field(default_factory=list)
    related_component_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReferenceNode(V2ContractModel):
    reference_node_id: str
    plane_id: str
    activation_applicable: bool = True


class ReferenceOverlayBinding(V2ContractModel):
    reference_node_id: str
    component_ids: list[str] = Field(default_factory=list)


class ReferenceCapabilityOverlay(V2ContractModel):
    reference_map_version: str = REFERENCE_MAP_VERSION
    bindings: list[ReferenceOverlayBinding] = Field(default_factory=list)


class ReferenceMapCatalog(V2ContractModel):
    version: str = REFERENCE_MAP_VERSION
    plane_ids: tuple[str, ...] = ()
    nodes: tuple[ReferenceNode, ...] = ()

    @classmethod
    def default(cls) -> ReferenceMapCatalog:
        from kai_mind.core.services.capability_reference_map_loader import (
            CapabilityReferenceMapLoader,
        )

        catalog = CapabilityReferenceMapLoader().load()
        return cls(
            version=catalog.version,
            plane_ids=catalog.plane_ids,
            nodes=tuple(
                ReferenceNode(
                    reference_node_id=node.id,
                    plane_id=node.plane_id,
                    activation_applicable=node.activation_applicable,
                )
                for node in catalog.nodes
            ),
        )

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @model_validator(mode="after")
    def _validate_catalog_shape(self) -> ReferenceMapCatalog:
        if len(self.plane_ids) != REFERENCE_PLANE_COUNT:
            raise ValueError("reference map must contain exactly 10 planes")
        if len(self.plane_ids) != len(set(self.plane_ids)):
            raise ValueError("reference map plane ids must be unique")
        if len(self.nodes) != REFERENCE_NODE_COUNT:
            raise ValueError(
                f"reference map must contain exactly {REFERENCE_NODE_COUNT} "
                "nodes"
            )
        node_ids = {node.reference_node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("reference map node ids must be unique")
        if any(node.plane_id not in self.plane_ids for node in self.nodes):
            raise ValueError("reference map node has an unknown plane_id")
        return self

    def validate_overlay(self, overlay: ReferenceCapabilityOverlay) -> None:
        if overlay.reference_map_version != self.version:
            raise ValueError(
                "overlay reference_map_version does not match catalog"
            )
        known = {node.reference_node_id for node in self.nodes}
        for binding in overlay.bindings:
            if binding.reference_node_id not in known:
                raise ValueError(
                    f"unknown reference_node_id: {binding.reference_node_id}"
                )
            if binding.reference_node_id in binding.component_ids:
                raise ValueError(
                    "reference node id must not be copied as component id"
                )


def build_ai_system_map_v2_schema() -> dict[str, Any]:
    schema = AiSystemMapV2.model_json_schema()
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = V2_SCHEMA_ID
    return schema
