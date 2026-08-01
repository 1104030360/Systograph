from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Final

from systograph.core.models.ai_system_map_v2 import (
    DEFAULT_ENVIRONMENT_ID,
    V2_SCHEMA_VERSION,
    V2_SYSTEM_TYPE,
    AiSystemMapV2,
    AiSystemMapV2CompatibilityView,
    AssessmentEvidenceKind,
    CanonicalCandidateFact,
    CanonicalCandidateFactMetadata,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEndpoint,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
    CanonicalLayer,
    CanonicalProject,
    CanonicalRecommendedNextCheck,
    CanonicalRiskHint,
    CanonicalUnmappedComponent,
    CompatibilityActivation,
    CompatibilityComponentStatus,
    CompatibilityProject,
    CompatibilityRiskTargetType,
    GenericCandidateFact,
    GenericCandidateFactMetadata,
    GenericComponent,
    GenericComponentMetadata,
    GenericEdge,
    GenericEdgeMetadata,
    GenericEndpoint,
    GenericEndpointMetadata,
    GenericRiskHint,
    GenericRiskHintMetadata,
    GenericUnmappedFact,
)
from systograph.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
    ExtensionComponent,
    RagSystemMap,
    RiskHint,
)
from systograph.core.services.legacy_slot_layer_map import SLOT_LAYER_BY_ID
from systograph.core.services.path_safety_service import (
    WINDOWS_DRIVE_RE,
    WINDOWS_UNC_RE,
)

SLOT_PLACEHOLDER_PREFIX: Final[str] = "component:slot_placeholder:"


@dataclass(frozen=True, slots=True)
class LegacySystemMapAdaptError(Exception):
    reason: str
    reference_id: str

    def __str__(self) -> str:
        return f"{self.reason}: {self.reference_id}"


@dataclass(frozen=True, slots=True)
class _ComponentIndex:
    components: list[GenericComponent]
    slot_target_ids: dict[str, str]
    known_component_ids: set[str]


class SystemMapV1ToV2Adapter:
    def adapt(
        self,
        system_map: RagSystemMap,
    ) -> AiSystemMapV2CompatibilityView:
        component_index = self._build_component_index(system_map)
        return AiSystemMapV2CompatibilityView(
            source_schema_version=system_map.schema_version,
            project=CompatibilityProject(
                name=system_map.project.name,
                root_path=system_map.project.root_path,
                root_path_redacted=system_map.project.root_path_redacted,
                path_mode=system_map.project.path_mode,
            ),
            components=component_index.components,
            edges=self._build_edges(system_map, component_index),
            evidence=[
                item.model_copy(deep=True) for item in system_map.evidence
            ],
            endpoints=self._build_endpoints(system_map, component_index),
            risk_hints=self._build_risk_hints(system_map, component_index),
            unmapped_facts=self._build_unmapped_facts(system_map),
            candidate_facts=self._build_candidate_facts(system_map),
            # Keep the v1 order: the list was service-sorted at build time.
            recommended_next_checks=[
                item.model_copy(deep=True)
                for item in system_map.recommended_next_checks
            ],
        )

    def adapt_to_canonical(
        self,
        system_map: RagSystemMap,
    ) -> AiSystemMapV2:
        """Adapt v1 map into normalized canonical ai-system-map/v2."""

        return self.to_canonical(self.adapt(system_map))

    def to_canonical(
        self,
        compatibility_view: AiSystemMapV2CompatibilityView,
    ) -> AiSystemMapV2:
        warnings = [
            "normalized_from_ai-system-map/v1",
            "active_output_remains_v1_until_plan_13",
        ]
        if compatibility_view.candidate_facts:
            warnings.append(
                "legacy_extension_candidates_preserved_as_candidate_facts"
            )

        root_path = compatibility_view.project.root_path
        if root_path is not None and _is_absolute_filesystem_path(root_path):
            root_path = None
            warnings.append("absolute_root_path_redacted_for_canonical_v2")

        return AiSystemMapV2(
            schema_version=V2_SCHEMA_VERSION,
            system_type=V2_SYSTEM_TYPE,
            source_schema_version="ai-system-map/v1",
            environment_id=DEFAULT_ENVIRONMENT_ID,
            migration_warnings=warnings,
            project=CanonicalProject(
                name=compatibility_view.project.name,
                root_path=root_path,
                root_path_redacted=(
                    compatibility_view.project.root_path_redacted
                ),
                path_mode=compatibility_view.project.path_mode,
            ),
            components=[
                CanonicalComponent(
                    component_id=item.component_id,
                    display_name=item.display_name,
                    canonical_type=item.canonical_type,
                    layer=item.layer,
                    status=item.status,
                    activation=item.activation,
                    evidence_ids=list(item.evidence_ids),
                    metadata=item.metadata.model_dump(mode="json"),
                )
                for item in compatibility_view.components
            ],
            edges=[
                CanonicalEdge(
                    edge_id=item.edge_id,
                    source=item.source,
                    target=item.target,
                    relationship=item.relationship,
                    status=item.status,
                    evidence_ids=list(item.evidence_ids),
                )
                for item in compatibility_view.edges
            ],
            evidence=[
                self._to_canonical_evidence(item)
                for item in compatibility_view.evidence
            ],
            endpoints=[
                CanonicalEndpoint(
                    endpoint_id=item.endpoint_id,
                    value=item.value,
                    endpoint_type=item.endpoint_type,
                    method=item.method,
                    component_id=item.component_id,
                    evidence_ids=[item.evidence_id],
                )
                for item in compatibility_view.endpoints
            ],
            risk_hints=[
                CanonicalRiskHint(
                    risk_id=item.risk_id,
                    type=item.type,
                    target=item.target,
                    target_type=item.target_type,
                    evidence_id=item.evidence_id,
                    rule_id=item.rule_id,
                    rationale=item.rationale,
                    uncertainty=item.uncertainty,
                    severity_hint=item.severity_hint,
                )
                for item in compatibility_view.risk_hints
            ],
            unmapped_components=[
                CanonicalUnmappedComponent(
                    unmapped_id=item.unmapped_fact_id,
                    observed_kind=item.observed_kind,
                    status=item.status,
                    reason=item.reason,
                    source_file=item.source_file,
                    evidence_ids=list(item.evidence_ids),
                    suggested_actions=list(item.suggested_actions),
                )
                for item in compatibility_view.unmapped_facts
            ],
            candidate_facts=[
                CanonicalCandidateFact(
                    candidate_fact_id=item.candidate_fact_id,
                    candidate_kind=item.candidate_kind,
                    display_name=item.display_name,
                    source_component_id=item.source_component_id,
                    evidence_ids=list(item.evidence_ids),
                    metadata=CanonicalCandidateFactMetadata(
                        source_extension_id=(
                            item.metadata.source_extension_id
                        ),
                        confirmed_by_user=item.metadata.confirmed_by_user,
                        source_status=item.metadata.source_status,
                    ),
                )
                for item in compatibility_view.candidate_facts
            ],
            recommended_next_checks=[
                CanonicalRecommendedNextCheck(
                    id=item.id,
                    target_type=item.target_type,
                    target=item.target,
                    reason=item.reason,
                    action=item.action,
                )
                for item in compatibility_view.recommended_next_checks
            ],
        )

    @staticmethod
    def _to_canonical_evidence(item: Evidence) -> CanonicalEvidence:
        json_pointer = (
            item.path
            if item.path is not None and item.path.startswith("/")
            else None
        )
        config_key = (
            item.path
            if item.path is not None and not item.path.startswith("/")
            else None
        )
        evidence_kind: AssessmentEvidenceKind
        if item.file is not None and (
            item.line_start is not None or json_pointer is not None
        ):
            evidence_kind = "direct"
        else:
            evidence_kind = "indirect"
        return CanonicalEvidence(
            evidence_id=item.id,
            artifact_type=item.kind,
            evidence_kind=evidence_kind,
            location=CanonicalEvidenceLocation(
                path=item.file,
                start_line=item.line_start,
                end_line=item.line_end,
                json_pointer=json_pointer,
                config_key=config_key,
            ),
            # v2 只有 extract_summary：優先 snippet，否則保留 value
            # （config/dependency 常無 snippet；--no-snippets 亦然）。
            extract_summary=item.snippet or item.value,
            rule_id=item.rule_id,
        )

    def _build_component_index(
        self,
        system_map: RagSystemMap,
    ) -> _ComponentIndex:
        components: list[GenericComponent] = []
        slot_target_ids: dict[str, str] = {}
        known_component_ids: set[str] = set()

        for slot_id in sorted(system_map.components_by_slot):
            slot = system_map.components_by_slot[slot_id]
            if len(slot.instances) == 1:
                component = self._component_from_instance(
                    slot,
                    slot.instances[0],
                )
                components.append(component)
                slot_target_ids[slot.slot] = component.component_id
                known_component_ids.add(component.component_id)
                continue

            if slot.instances:
                sorted_instances = sorted(
                    slot.instances,
                    key=lambda item: item.id,
                )
                for instance in sorted_instances:
                    component = self._component_from_instance(slot, instance)
                    components.append(component)
                    known_component_ids.add(component.component_id)

            placeholder = self._slot_placeholder_component(slot)
            components.append(placeholder)
            slot_target_ids[slot.slot] = placeholder.component_id
            known_component_ids.add(placeholder.component_id)

        sorted_extensions = sorted(
            system_map.extensions,
            key=lambda item: item.id,
        )
        for extension in sorted_extensions:
            component = self._component_from_extension(extension)
            components.append(component)
            known_component_ids.add(component.component_id)

        return _ComponentIndex(
            components=components,
            slot_target_ids=slot_target_ids,
            known_component_ids=known_component_ids,
        )

    def _component_from_instance(
        self,
        slot: ComponentSlot,
        instance: ComponentInstance,
    ) -> GenericComponent:
        return GenericComponent(
            component_id=instance.id,
            display_name=instance.name,
            canonical_type=instance.kind,
            layer=_layer_for_slot(slot.slot),
            status=slot.status,
            activation=_activation_for_status(slot.status),
            evidence_ids=sorted(instance.evidence_ids),
            metadata=GenericComponentMetadata(
                legacy_slot=slot.slot,
                source_component_id=instance.id,
                source_extension_id=None,
                semantic_kind="repo_component",
                required_for_rag=slot.required_for_rag,
                source_status=slot.status,
                source_kind=instance.kind,
            ),
        )

    def _slot_placeholder_component(
        self,
        slot: ComponentSlot,
    ) -> GenericComponent:
        return GenericComponent(
            component_id=_slot_placeholder_id(slot.slot),
            display_name=_humanize(slot.slot),
            canonical_type="slot_placeholder",
            layer=_layer_for_slot(slot.slot),
            status=slot.status,
            activation=_activation_for_status(slot.status),
            evidence_ids=sorted(
                {
                    evidence_id
                    for instance in slot.instances
                    for evidence_id in instance.evidence_ids
                }
            ),
            metadata=GenericComponentMetadata(
                legacy_slot=slot.slot,
                source_component_id=None,
                source_extension_id=None,
                semantic_kind="slot_placeholder",
                required_for_rag=slot.required_for_rag,
                source_status=slot.status,
                source_kind="slot_placeholder",
            ),
        )

    def _component_from_extension(
        self,
        extension: ExtensionComponent,
    ) -> GenericComponent:
        status, activation = _extension_assessment_state(extension)
        return GenericComponent(
            component_id=extension.id,
            display_name=extension.name,
            canonical_type="legacy_extension",
            layer="extension_subsystems",
            status=status,
            activation=activation,
            evidence_ids=sorted(extension.evidence_ids),
            metadata=GenericComponentMetadata(
                legacy_slot=None,
                source_component_id=None,
                source_extension_id=extension.id,
                semantic_kind="legacy_extension",
                required_for_rag=None,
                source_status=extension.status,
                source_kind=extension.kind,
            ),
        )

    def _build_edges(
        self,
        system_map: RagSystemMap,
        component_index: _ComponentIndex,
    ) -> list[GenericEdge]:
        edges: list[GenericEdge] = []
        for flow in system_map.flows:
            for edge in flow.edges:
                edges.append(
                    GenericEdge(
                        edge_id=edge.id,
                        source=self._resolve_component_id(
                            component_id=edge.from_component_id,
                            slot=edge.from_slot,
                            reference_id=edge.id,
                            endpoint_role="source",
                            component_index=component_index,
                        ),
                        target=self._resolve_component_id(
                            component_id=edge.to_component_id,
                            slot=edge.to_slot,
                            reference_id=edge.id,
                            endpoint_role="target",
                            component_index=component_index,
                        ),
                        relationship=edge.relationship,
                        status="observed",
                        evidence_ids=sorted(edge.evidence_ids),
                        metadata=GenericEdgeMetadata(
                            source_edge_id=edge.id,
                            flow_id=edge.flow_id,
                            from_slot=edge.from_slot,
                            to_slot=edge.to_slot,
                        ),
                    )
                )
        return sorted(edges, key=lambda item: item.edge_id)

    def _build_endpoints(
        self,
        system_map: RagSystemMap,
        component_index: _ComponentIndex,
    ) -> list[GenericEndpoint]:
        endpoints = [
            GenericEndpoint(
                endpoint_id=endpoint.id,
                value=endpoint.value,
                endpoint_type=endpoint.endpoint_type,
                method=endpoint.method,
                component_id=self._resolve_optional_component_id(
                    component_id=endpoint.component_instance_id,
                    slot=endpoint.slot,
                    reference_id=endpoint.id,
                    component_index=component_index,
                ),
                evidence_id=endpoint.evidence_id,
                metadata=GenericEndpointMetadata(
                    source_endpoint_id=endpoint.id,
                    legacy_slot=endpoint.slot,
                    source_component_id=endpoint.component_instance_id,
                ),
            )
            for endpoint in system_map.endpoints
        ]
        return sorted(endpoints, key=lambda item: item.endpoint_id)

    def _build_risk_hints(
        self,
        system_map: RagSystemMap,
        component_index: _ComponentIndex,
    ) -> list[GenericRiskHint]:
        risks = [
            self._risk_hint(risk, component_index)
            for risk in system_map.risk_hints
        ]
        return sorted(risks, key=lambda item: item.risk_id)

    def _risk_hint(
        self,
        risk: RiskHint,
        component_index: _ComponentIndex,
    ) -> GenericRiskHint:
        target, target_type = self._resolve_risk_target(
            risk,
            component_index,
        )
        return GenericRiskHint(
            risk_id=risk.id,
            type=risk.type,
            target=target,
            target_type=target_type,
            evidence_id=risk.evidence_id,
            rule_id=risk.rule_id,
            rationale=risk.rationale,
            uncertainty=risk.uncertainty,
            severity_hint=risk.severity_hint,
            metadata=GenericRiskHintMetadata(
                source_risk_id=risk.id,
                source_target=risk.target,
                source_target_type=risk.target_type,
            ),
        )

    def _resolve_risk_target(
        self,
        risk: RiskHint,
        component_index: _ComponentIndex,
    ) -> tuple[str, CompatibilityRiskTargetType]:
        match risk.target_type:
            case "component_instance":
                return (
                    self._require_known_component_id(
                        component_id=risk.target,
                        reference_id=risk.id,
                        known_component_ids=component_index.known_component_ids,
                    ),
                    "component",
                )
            case "component_slot":
                return (
                    self._resolve_slot_target_id(
                        slot=risk.target,
                        reference_id=risk.id,
                        component_index=component_index,
                    ),
                    "component",
                )
            case "endpoint":
                return (risk.target, "endpoint")
            case "evidence":
                return (risk.target, "evidence")
            case "file":
                return (risk.target, "file")
            case _:
                raise LegacySystemMapAdaptError(
                    reason="unsupported_risk_target_type",
                    reference_id=f"{risk.id}:{risk.target_type}",
                )

    def _build_unmapped_facts(
        self,
        system_map: RagSystemMap,
    ) -> list[GenericUnmappedFact]:
        facts = [
            GenericUnmappedFact(
                unmapped_fact_id=item.id,
                observed_kind=item.observed_kind,
                status=item.status,
                reason=item.reason,
                source_file=item.source_file,
                evidence_ids=sorted(item.evidence_ids),
                suggested_actions=list(item.suggested_actions),
            )
            for item in system_map.unmapped_components
        ]
        return sorted(facts, key=lambda item: item.unmapped_fact_id)

    def _build_candidate_facts(
        self,
        system_map: RagSystemMap,
    ) -> list[GenericCandidateFact]:
        candidates = [
            GenericCandidateFact(
                candidate_fact_id=f"candidate:legacy_extension:{extension.id}",
                candidate_kind="legacy_extension",
                display_name=extension.name,
                source_component_id=extension.id,
                evidence_ids=sorted(extension.evidence_ids),
                metadata=GenericCandidateFactMetadata(
                    source_extension_id=extension.id,
                    confirmed_by_user=extension.confirmed_by_user,
                    source_status=extension.status,
                ),
            )
            for extension in system_map.extensions
        ]
        return sorted(candidates, key=lambda item: item.candidate_fact_id)

    def _resolve_optional_component_id(
        self,
        *,
        component_id: str | None,
        slot: str | None,
        reference_id: str,
        component_index: _ComponentIndex,
    ) -> str | None:
        if component_id is not None:
            return self._require_known_component_id(
                component_id=component_id,
                reference_id=reference_id,
                known_component_ids=component_index.known_component_ids,
            )
        if slot is None:
            return None
        return self._resolve_slot_target_id(
            slot=slot,
            reference_id=reference_id,
            component_index=component_index,
        )

    def _resolve_component_id(
        self,
        *,
        component_id: str | None,
        slot: str,
        reference_id: str,
        endpoint_role: str,
        component_index: _ComponentIndex,
    ) -> str:
        if component_id is not None:
            return self._require_known_component_id(
                component_id=component_id,
                reference_id=reference_id,
                known_component_ids=component_index.known_component_ids,
            )
        try:
            return self._resolve_slot_target_id(
                slot=slot,
                reference_id=reference_id,
                component_index=component_index,
            )
        except LegacySystemMapAdaptError as exc:
            raise LegacySystemMapAdaptError(
                reason=f"missing_{endpoint_role}_component_reference",
                reference_id=f"{reference_id}:{slot}",
            ) from exc

    def _resolve_slot_target_id(
        self,
        *,
        slot: str,
        reference_id: str,
        component_index: _ComponentIndex,
    ) -> str:
        target_id = component_index.slot_target_ids.get(slot)
        if target_id is None:
            raise LegacySystemMapAdaptError(
                reason="unknown_legacy_slot",
                reference_id=f"{reference_id}:{slot}",
            )
        return target_id

    def _require_known_component_id(
        self,
        *,
        component_id: str,
        reference_id: str,
        known_component_ids: set[str],
    ) -> str:
        if component_id in known_component_ids:
            return component_id
        raise LegacySystemMapAdaptError(
            reason="unknown_component_id",
            reference_id=f"{reference_id}:{component_id}",
        )


def _slot_placeholder_id(slot: str) -> str:
    return f"{SLOT_PLACEHOLDER_PREFIX}{slot}"


def _layer_for_slot(slot: str) -> CanonicalLayer:
    return SLOT_LAYER_BY_ID.get(slot, "undetermined")


def _activation_for_status(
    status: CompatibilityComponentStatus | str,
) -> CompatibilityActivation:
    match status:
        case "detected" | "confirmed":
            return "enabled"
        case "not_configured":
            return "disabled"
        case "not_applicable":
            return "not_applicable"
        case "missing":
            return "unknown"
        case _:
            raise LegacySystemMapAdaptError(
                reason="unsupported_component_status",
                reference_id=status,
            )


def _extension_assessment_state(
    extension: ExtensionComponent,
) -> tuple[CompatibilityComponentStatus, CompatibilityActivation]:
    """Map legacy extension confirmation into non-capability assessment state.

    Unconfirmed candidates stay undetermined/unknown so migration never auto-
    declares a capability as detected/confirmed.
    """

    if extension.confirmed_by_user is True or extension.status == "confirmed":
        return ("confirmed", "enabled")
    return ("undetermined", "unknown")


def _is_absolute_filesystem_path(value: str) -> bool:
    if value in {"", ".", "<project_root>"}:
        return False
    if WINDOWS_DRIVE_RE.match(value) or WINDOWS_UNC_RE.match(value):
        return True
    if "\\" in value:
        return PureWindowsPath(value).is_absolute()
    return PurePosixPath(value).is_absolute()


def _humanize(value: str) -> str:
    return value.replace("_", " ").title()
