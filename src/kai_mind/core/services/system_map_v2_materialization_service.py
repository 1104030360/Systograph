from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.mapping import ManualMapping
from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from kai_mind.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from kai_mind.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from kai_mind.core.services.manual_mapping_service import ManualMappingService
from kai_mind.core.services.rag_template_service import RagTemplateService
from kai_mind.core.services.recommended_next_check_service import (
    RecommendedNextCheckService,
)
from kai_mind.core.services.risk_hint_service import RiskHintService
from kai_mind.core.services.system_map_v2_normalize_service import (
    SystemMapV2NormalizeService,
)
from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)


@dataclass(frozen=True, slots=True)
class SystemMapV2MaterializationResult:
    system_map: AiSystemMapV2
    detection: ComponentDetectionResult
    manual_mappings: tuple[ManualMapping, ...] = ()


class SystemMapV2MaterializationService:
    def __init__(
        self,
        *,
        component_detection_service: ComponentDetectionService | None = None,
        endpoint_detection_service: EndpointDetectionService | None = None,
        risk_hint_service: RiskHintService | None = None,
        flow_derivation_service: FlowDerivationService | None = None,
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
        flows = self._flow_derivation_service.derive(
            template=template,
            components=detection,
        )
        system_map = self._normalize_service.assemble(
            project_name=project_name,
            project_id=project_id,
            project_root=project_root,
            raw_scan=raw_scan,
            components=detection,
            endpoints=endpoints,
            flows=flows,
            risk_hints=risk_hints,
            recommended_next_checks=recommended_next_checks,
            no_snippets=request.no_snippets,
        )
        validated = self._validation_service.validate(
            system_map.model_dump(mode="json")
        )
        return SystemMapV2MaterializationResult(
            system_map=validated,
            detection=detection,
            manual_mappings=manual_mappings,
        )
