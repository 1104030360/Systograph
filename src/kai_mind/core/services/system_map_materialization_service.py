from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.mapping import ManualMapping
from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.models.system_map import Evidence, Project, RagSystemMap
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
from kai_mind.core.services.risk_hint_service import RiskHintService
from kai_mind.core.services.system_map_normalize_service import (
    SystemMapNormalizeService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


@dataclass(frozen=True, slots=True)
class SystemMapMaterializationResult:
    system_map: RagSystemMap
    detection: ComponentDetectionResult
    manual_mappings: tuple[ManualMapping, ...] = ()


class SystemMapMaterializationService:
    def __init__(
        self,
        *,
        component_detection_service: ComponentDetectionService | None = None,
        endpoint_detection_service: EndpointDetectionService | None = None,
        risk_hint_service: RiskHintService | None = None,
        flow_derivation_service: FlowDerivationService | None = None,
        manual_mapping_service: ManualMappingService | None = None,
        normalize_service: SystemMapNormalizeService | None = None,
        validation_service: SystemMapValidationService | None = None,
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
        self._normalize_service = (
            normalize_service or SystemMapNormalizeService()
        )
        self._validation_service = (
            validation_service or SystemMapValidationService()
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
    ) -> SystemMapMaterializationResult:
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
        flows = self._flow_derivation_service.derive(
            template=template,
            components=detection,
        )
        assembled = self._normalize_service.assemble(
            project_name=project_name,
            raw_scan=raw_scan,
            template=template,
            components=detection,
            endpoints=endpoints,
            flows=flows,
            risk_hints=risk_hints,
        )
        adjusted = self._apply_request_options(
            system_map=assembled,
            project_root=project_root,
            request=request,
        )
        validated = self._validation_service.validate(
            adjusted.model_dump(mode="json")
        )
        return SystemMapMaterializationResult(
            validated,
            detection,
            manual_mappings,
        )

    @staticmethod
    def _apply_request_options(
        *,
        system_map: RagSystemMap,
        project_root: Path,
        request: MapBuildRequest,
    ) -> RagSystemMap:
        project = system_map.project
        if not request.redact_root_path:
            project = Project(
                name=project.name,
                root_path=str(project_root),
                root_path_redacted=None,
                path_mode="absolute",
                system_map_schema_version=project.system_map_schema_version,
            )
        evidence = system_map.evidence
        if request.no_snippets:
            evidence = [
                Evidence(**item.model_dump(mode="python", exclude={"snippet"}))
                for item in evidence
            ]
        if project is system_map.project and evidence is system_map.evidence:
            return system_map
        return system_map.model_copy(
            update={"project": project, "evidence": evidence}
        )
