"""Orchestrate project folder scans into canonical map artifacts."""

from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.models.system_map import Evidence, Project, RagSystemMap
from kai_mind.core.models.template import RagTemplate
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
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
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.markdown_summary_service import (
    MarkdownSummaryService,
)
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.rag_template_service import RagTemplateService
from kai_mind.core.services.risk_hint_service import RiskHintService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.system_map_normalize_service import (
    SystemMapNormalizeService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService


class MapBuildService:
    """Build validated map artifacts through the shared core pipeline."""

    def __init__(
        self,
        *,
        output_artifact_provider: OutputArtifactProvider | None = None,
        project_scan_service: ProjectScanService | None = None,
        component_detection_service: ComponentDetectionService | None = None,
        endpoint_detection_service: EndpointDetectionService | None = None,
        risk_hint_service: RiskHintService | None = None,
        flow_derivation_service: FlowDerivationService | None = None,
        manual_mapping_service: ManualMappingService | None = None,
        normalize_service: SystemMapNormalizeService | None = None,
        markdown_summary_service: MarkdownSummaryService | None = None,
        projection_service: ViewerSessionService | None = None,
        validation_service: SystemMapValidationService | None = None,
        scan_boundary_review_service: ScanBoundaryReviewService | None = None,
    ) -> None:
        self._output_artifact_provider = (
            output_artifact_provider or OutputArtifactProvider()
        )
        self._project_scan_service = (
            project_scan_service or ProjectScanService()
        )
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
        self._markdown_summary_service = (
            markdown_summary_service or MarkdownSummaryService()
        )
        self._projection_service = projection_service or ViewerSessionService()
        self._validation_service = (
            validation_service or SystemMapValidationService()
        )
        self._scan_boundary_review_service = scan_boundary_review_service

    def build(
        self,
        request: MapBuildRequest,
        *,
        project_id: str | None = None,
    ) -> MapBuildResult:
        """Build map artifacts and a frontend viewer payload."""

        precondition = self._output_artifact_provider.check_preconditions(
            project_path=request.project_path,
            output_dir=request.output,
        )
        project_name = request.project_path.name or "project"
        if not precondition.ok:
            return self._precondition_error_result(
                project_name=project_name,
                error=precondition.error,
                output_run=precondition.output_run,
                warnings=precondition.warnings,
            )

        if (
            precondition.project_root is None
            or precondition.output_run is None
        ):
            raise ValueError("Precondition result is missing resolved paths")

        system_map = self._build_system_map(
            project_root=precondition.project_root,
            project_name=precondition.project_root.name,
            request=request,
            project_id=project_id,
        )
        map_json_path = self._output_artifact_provider.write_json(
            system_map,
            output_run=precondition.output_run,
        )
        markdown = self._markdown_summary_service.render(system_map)
        map_markdown_path = self._output_artifact_provider.write_markdown(
            markdown,
            output_run=precondition.output_run,
        )
        viewer_load_result = self._projection_service.build(
            system_map,
            map_json_path=map_json_path,
        )

        return MapBuildResult(
            status="ok",
            project_name=precondition.project_root.name,
            output_run_dir=precondition.output_run.root_dir,
            map_json_path=map_json_path,
            map_markdown_path=map_markdown_path,
            map_error_path=None,
            viewer_load_result=viewer_load_result,
            ai_system_map=system_map,
            warnings=precondition.warnings,
            error=None,
        )

    def _precondition_error_result(
        self,
        *,
        project_name: str,
        error: PreconditionError | None,
        output_run: OutputRun | None,
        warnings: list[str],
    ) -> MapBuildResult:
        map_error_path: Path | None = None
        if error is not None and output_run is not None:
            map_error_path = self._output_artifact_provider.write_map_error(
                error,
                output_run=output_run,
            )

        return MapBuildResult(
            status="error",
            project_name=project_name,
            output_run_dir=output_run.root_dir if output_run else None,
            map_json_path=None,
            map_markdown_path=None,
            map_error_path=map_error_path,
            viewer_load_result=None,
            ai_system_map=None,
            warnings=warnings,
            error=error,
        )

    def _build_system_map(
        self,
        *,
        project_root: Path,
        project_name: str,
        request: MapBuildRequest,
        project_id: str | None,
    ) -> RagSystemMap:
        raw_scan = self._scan_project(
            project_root=project_root,
            project_id=project_id,
        )
        template = RagTemplateService.load("rag-core-v1")
        components = self._detect_components(
            raw_scan=raw_scan,
            template=template,
            project_id=project_id,
        )
        endpoints = self._endpoint_detection_service.detect(
            facts=raw_scan.facts,
            evidence=raw_scan.evidence,
            components=components,
        )
        risk_hints = self._risk_hint_service.derive(
            facts=raw_scan.facts,
            evidence=raw_scan.evidence,
            issues=raw_scan.issues,
            components=components,
            endpoints=endpoints,
        )
        flows = self._flow_derivation_service.derive(
            template=template,
            components=components,
        )
        system_map = self._normalize_service.normalize(
            project_name=project_name,
            raw_scan=raw_scan,
            template=template,
            components=components,
            endpoints=endpoints,
            flows=flows,
            risk_hints=risk_hints,
        )
        return self._apply_request_options(
            system_map=system_map,
            project_root=project_root,
            request=request,
        )

    def _scan_project(
        self,
        *,
        project_root: Path,
        project_id: str | None,
    ) -> ProjectScanResult:
        if project_id is None or self._scan_boundary_review_service is None:
            return self._project_scan_service.scan(project_root)

        return self._project_scan_service.scan(
            project_root,
            inventory_policy=self._scan_boundary_review_service.for_project(
                project_id
            ),
        )

    def _detect_components(
        self,
        *,
        raw_scan: ProjectScanResult,
        template: RagTemplate,
        project_id: str | None,
    ) -> ComponentDetectionResult:
        result = self._component_detection_service.detect(
            template=template,
            facts=raw_scan.facts,
            evidence=raw_scan.evidence,
        )
        if project_id is not None and self._manual_mapping_service is not None:
            return self._manual_mapping_service.for_project(project_id).apply(
                result
            )
        return result

    def _apply_request_options(
        self,
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

        return self._validation_service.validate(
            system_map.model_copy(
                update={
                    "project": project,
                    "evidence": evidence,
                }
            ).model_dump(mode="json")
        )
