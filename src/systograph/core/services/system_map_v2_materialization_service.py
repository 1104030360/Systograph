from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.mapping import ManualMapping
from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.scan import ProjectScanResult
from systograph.core.models.structural_fact import StructuralFact
from systograph.core.models.system_map import ComponentInstance, Evidence
from systograph.core.services.call_priority_edge_merge_service import (
    CallPriorityEdgeMergeService,
)
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from systograph.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.rag_template_service import RagTemplateService
from systograph.core.services.recommended_next_check_service import (
    RecommendedNextCheckService,
)
from systograph.core.services.risk_hint_service import RiskHintService
from systograph.core.services.system_map_v2_normalize_service import (
    SystemMapV2NormalizeService,
)
from systograph.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)
from systograph.core.services.ua_edge_derivation_models import (
    UaEdgeDerivationResult,
)
from systograph.core.services.ua_edge_derivation_service import (
    UaEdgeDerivationService,
)

TEMPLATE_FLOW_EDGES_ENV = "SYSTOGRAPH_TEMPLATE_FLOW_EDGES"


class UaEdgeDeriver(Protocol):
    def derive(
        self,
        *,
        components: Sequence[ComponentInstance],
        evidence: Sequence[Evidence],
        structural_facts: Sequence[StructuralFact],
    ) -> UaEdgeDerivationResult: ...


@dataclass(frozen=True, slots=True)
class SystemMapV2MaterializationResult:
    system_map: AiSystemMapV2
    detection: ComponentDetectionResult
    manual_mappings: tuple[ManualMapping, ...] = ()
    warnings: tuple[str, ...] = ()


class SystemMapV2MaterializationService:
    def __init__(
        self,
        *,
        component_detection_service: ComponentDetectionService | None = None,
        endpoint_detection_service: EndpointDetectionService | None = None,
        risk_hint_service: RiskHintService | None = None,
        flow_derivation_service: FlowDerivationService | None = None,
        ua_edge_derivation_service: UaEdgeDeriver | None = None,
        edge_merge_service: CallPriorityEdgeMergeService | None = None,
        manual_mapping_service: ManualMappingService | None = None,
        recommended_next_check_service: (
            RecommendedNextCheckService | None
        ) = None,
        normalize_service: SystemMapV2NormalizeService | None = None,
        validation_service: SystemMapV2ValidationService | None = None,
    ) -> None:
        self._component_detection_service = (
            component_detection_service or ComponentDetectionService()
        )
        self._endpoint_detection_service = (
            endpoint_detection_service or EndpointDetectionService()
        )
        self._risk_hint_service = risk_hint_service or RiskHintService()
        self._flow_derivation_service = (
            flow_derivation_service or FlowDerivationService()
        )
        self._ua_edge_derivation_service = (
            ua_edge_derivation_service or UaEdgeDerivationService()
        )
        self._edge_merge_service = (
            edge_merge_service or CallPriorityEdgeMergeService()
        )
        self._manual_mapping_service = manual_mapping_service
        self._recommended_next_check_service = (
            recommended_next_check_service or RecommendedNextCheckService()
        )
        self._normalize_service = (
            normalize_service or SystemMapV2NormalizeService()
        )
        self._validation_service = (
            validation_service or SystemMapV2ValidationService()
        )

    def materialize(
        self,
        *,
        raw_scan: ProjectScanResult,
        project_name: str,
        project_root: Path,
        request: MapBuildRequest,
        project_id: str | None,
        mapping_ids: tuple[str, ...] | None = None,
    ) -> SystemMapV2MaterializationResult:
        template = RagTemplateService.load("rag-core-v1")
        detection = self._component_detection_service.detect(
            template=template,
            facts=raw_scan.facts,
            evidence=raw_scan.evidence,
            structural_facts=raw_scan.structural_facts,
        )
        manual_mappings: tuple[ManualMapping, ...] = ()
        if project_id is not None and self._manual_mapping_service is not None:
            project_mappings = self._manual_mapping_service.for_project(
                project_id
            )
            manual_mappings = tuple(
                project_mappings.list_for_project(project_id)
            )
            detection = (
                project_mappings.apply(detection)
                if mapping_ids is None
                else project_mappings.apply_selected(detection, mapping_ids)
            )
        endpoints = self._endpoint_detection_service.detect(
            facts=raw_scan.facts,
            evidence=raw_scan.evidence,
            components=detection,
        )
        risk_hints = self._risk_hint_service.derive(
            facts=raw_scan.facts,
            evidence=raw_scan.evidence,
            issues=raw_scan.issues,
            components=detection,
            endpoints=endpoints,
        )
        recommended_next_checks = self._recommended_next_check_service.derive(
            raw_scan=raw_scan,
            components=detection,
            endpoints=endpoints,
            risk_hints=risk_hints,
        )
        edge_derivation = self._ua_edge_derivation_service.derive(
            components=_component_instances(detection),
            evidence=raw_scan.evidence,
            structural_facts=raw_scan.structural_facts,
        )
        recommended_next_checks = _merge_recommended_checks(
            recommended_next_checks,
            edge_derivation.recommended_next_checks,
        )
        flows = (
            self._flow_derivation_service.derive(
                template=template,
                components=detection,
            )
            if template_flow_edges_enabled()
            else []
        )
        merged_edges = self._edge_merge_service.merge(
            structural_edges=edge_derivation.edges,
            template_flows=flows,
        )
        system_map = self._normalize_service.assemble(
            project_name=project_name,
            project_id=project_id,
            project_root=project_root,
            raw_scan=raw_scan,
            components=detection,
            endpoints=endpoints,
            edges=merged_edges.edges,
            risk_hints=risk_hints,
            recommended_next_checks=recommended_next_checks,
            no_snippets=request.no_snippets,
        )
        validated = self._validation_service.validate(
            system_map.model_dump(mode="json")
        )
        warnings = list(edge_derivation.warnings)
        if merged_edges.discarded_lower_tier:
            warnings.append(
                "UA edge derivation discarded lower-tier L2/L3="
                f"{merged_edges.discarded_lower_tier}"
            )
        return SystemMapV2MaterializationResult(
            system_map=validated,
            detection=detection,
            manual_mappings=manual_mappings,
            warnings=tuple(warnings),
        )


def template_flow_edges_enabled() -> bool:
    value = os.environ.get(TEMPLATE_FLOW_EDGES_ENV, "on").strip().lower()
    if value not in {"on", "off"}:
        raise ValueError(
            f"{TEMPLATE_FLOW_EDGES_ENV} must be 'on' or 'off', got {value!r}"
        )
    return value == "on"


def _component_instances(
    detection: ComponentDetectionResult,
) -> tuple[ComponentInstance, ...]:
    return tuple(
        instance
        for slot_id in sorted(detection.components_by_slot)
        for instance in sorted(
            detection.components_by_slot[slot_id].instances,
            key=lambda item: item.id,
        )
    )


def _merge_recommended_checks(
    primary: Sequence[RecommendedNextCheck],
    edge_checks: Sequence[RecommendedNextCheck],
) -> list[RecommendedNextCheck]:
    by_id = {item.id: item for item in (*primary, *edge_checks)}
    return [by_id[item_id] for item_id in sorted(by_id)]
