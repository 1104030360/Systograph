from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from systograph.core.models.ai_system_map_v2 import (
    V2_SCHEMA_VERSION,
    V2_SYSTEM_TYPE,
    ActivationState,
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEndpoint,
    CanonicalProject,
    CanonicalRecommendedNextCheck,
    CanonicalRiskHint,
    CanonicalUnmappedComponent,
    DetectionStatus,
    RiskTargetTypeV2,
)
from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.scan import ProjectScanResult
from systograph.core.models.system_map import Endpoint, Flow, RiskHint
from systograph.core.services.canonical_evidence_service import (
    canonical_evidence_from_scan,
)
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from systograph.core.services.legacy_slot_layer_map import SLOT_LAYER_BY_ID


class SystemMapV2NormalizeService:
    def assemble(
        self,
        *,
        project_name: str,
        project_id: str | None,
        project_root: Path,
        raw_scan: ProjectScanResult,
        components: ComponentDetectionResult,
        endpoints: Sequence[Endpoint],
        flows: Sequence[Flow],
        risk_hints: Sequence[RiskHint],
        recommended_next_checks: Sequence[RecommendedNextCheck],
        no_snippets: bool,
    ) -> AiSystemMapV2:
        canonical_components = self._components(components)
        component_ids = {
            component.component_id for component in canonical_components
        }
        return AiSystemMapV2(
            schema_version=V2_SCHEMA_VERSION,
            system_type=V2_SYSTEM_TYPE,
            source_schema_version="ai-system-map/v2",
            project=CanonicalProject(
                project_id=project_id,
                name=project_name,
                root_path="<project_root>",
                root_path_redacted="<project_root>",
                path_mode="redacted",
            ),
            components=canonical_components,
            edges=self._edges(flows, component_ids),
            evidence=[
                canonical_evidence_from_scan(
                    item,
                    no_snippets=no_snippets,
                )
                for item in sorted(raw_scan.evidence, key=lambda item: item.id)
            ],
            endpoints=self._endpoints(endpoints, component_ids),
            risk_hints=self._risk_hints(
                risk_hints,
                components=components,
                component_ids=component_ids,
            ),
            unmapped_components=[
                CanonicalUnmappedComponent(
                    unmapped_id=item.id,
                    observed_kind=item.observed_kind,
                    status=item.status,
                    reason=item.reason,
                    source_file=item.source_file,
                    evidence_ids=sorted(item.evidence_ids),
                    suggested_actions=list(item.suggested_actions),
                )
                for item in sorted(
                    components.unmapped_components,
                    key=lambda item: item.id,
                )
            ],
            # Order is the RecommendedNextCheckService output order
            # (sorted by id); assembling must not reorder it.
            recommended_next_checks=[
                CanonicalRecommendedNextCheck(
                    id=check.id,
                    target_type=check.target_type,
                    target=check.target,
                    reason=check.reason,
                    action=check.action,
                )
                for check in recommended_next_checks
            ],
        )

    @staticmethod
    def _components(
        detected: ComponentDetectionResult,
    ) -> list[CanonicalComponent]:
        result: list[CanonicalComponent] = []
        for slot_id in sorted(detected.components_by_slot):
            slot = detected.components_by_slot[slot_id]
            for instance in sorted(slot.instances, key=lambda item: item.id):
                result.append(
                    CanonicalComponent(
                        component_id=instance.id,
                        display_name=instance.name,
                        canonical_type=instance.kind,
                        layer=SLOT_LAYER_BY_ID.get(slot.slot, "undetermined"),
                        status=cast(DetectionStatus, slot.status),
                        activation=_activation(slot.status),
                        evidence_ids=sorted(instance.evidence_ids),
                        framework=instance.provider,
                        metadata={
                            "legacy_slot": slot.slot,
                            "required_for_rag": slot.required_for_rag,
                            "semantic_kind": "repo_component",
                        },
                    )
                )
        return result

    @staticmethod
    def _edges(
        flows: Sequence[Flow],
        component_ids: set[str],
    ) -> list[CanonicalEdge]:
        result: list[CanonicalEdge] = []
        for flow in sorted(flows, key=lambda item: item.id):
            for edge in sorted(flow.edges, key=lambda item: item.id):
                if (
                    edge.from_component_id not in component_ids
                    or edge.to_component_id not in component_ids
                ):
                    continue
                result.append(
                    CanonicalEdge(
                        edge_id=edge.id,
                        source=edge.from_component_id,
                        target=edge.to_component_id,
                        relationship=edge.relationship,
                        status="observed",
                        evidence_ids=sorted(edge.evidence_ids),
                    )
                )
        return result

    @staticmethod
    def _endpoints(
        endpoints: Sequence[Endpoint],
        component_ids: set[str],
    ) -> list[CanonicalEndpoint]:
        return [
            CanonicalEndpoint(
                endpoint_id=item.id,
                value=item.value,
                endpoint_type=item.endpoint_type,
                method=item.method,
                component_id=(
                    item.component_instance_id
                    if item.component_instance_id in component_ids
                    else None
                ),
                evidence_ids=[item.evidence_id],
            )
            for item in sorted(endpoints, key=lambda item: item.id)
        ]

    @staticmethod
    def _risk_hints(
        risks: Sequence[RiskHint],
        *,
        components: ComponentDetectionResult,
        component_ids: set[str],
    ) -> list[CanonicalRiskHint]:
        result: list[CanonicalRiskHint] = []
        for item in sorted(risks, key=lambda item: item.id):
            target = item.target
            target_type = cast(RiskTargetTypeV2, item.target_type)
            if item.target_type == "component_instance":
                target_type = "component"
                if target not in component_ids:
                    target = item.evidence_id
                    target_type = "evidence"
            elif item.target_type == "component_slot":
                slot = components.components_by_slot.get(item.target)
                instance = (
                    sorted(slot.instances, key=lambda value: value.id)[0]
                    if slot is not None and slot.instances
                    else None
                )
                if instance is None:
                    target = item.evidence_id
                    target_type = "evidence"
                else:
                    target = instance.id
                    target_type = "component"
            result.append(
                CanonicalRiskHint(
                    risk_id=item.id,
                    type=item.type,
                    target=target,
                    target_type=target_type,
                    evidence_id=item.evidence_id,
                    rule_id=item.rule_id,
                    rationale=item.rationale,
                    uncertainty=item.uncertainty,
                    severity_hint=item.severity_hint,
                )
            )
        return result


def _activation(status: str) -> ActivationState:
    if status == "detected":
        return "enabled"
    if status == "not_applicable":
        return "not_applicable"
    if status == "not_configured":
        return "disabled"
    return "unknown"
