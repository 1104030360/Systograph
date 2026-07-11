from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from kai_mind.core.models.analysis_history import (
    BuildReason,
    MapBuildLineage,
    ScanSnapshot,
)
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.scan import OutputRun
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.build_artifact_publisher import (
    BuildArtifactPublisher,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionService,
)
from kai_mind.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from kai_mind.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from kai_mind.core.services.manual_mapping_service import ManualMappingService
from kai_mind.core.services.map_build_orchestration import (
    precondition_error_result,
    scan_project,
)
from kai_mind.core.services.map_build_pipeline import MapBuildPipeline
from kai_mind.core.services.markdown_summary_service import (
    MarkdownSummaryService,
)
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from kai_mind.core.services.readiness_report_service import (
    ReadinessReportService,
)
from kai_mind.core.services.risk_hint_service import RiskHintService
from kai_mind.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)
from kai_mind.core.services.system_map_materialization_service import (
    SystemMapMaterializationService,
)
from kai_mind.core.services.system_map_normalize_service import (
    SystemMapNormalizeService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService


class MapBuildService:
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
        canonical_map_loader: CanonicalMapLoader | None = None,
        profile_inference_service: ProfileInferenceService | None = None,
        readiness_report_service: ReadinessReportService | None = None,
        static_execution_artifact_service: (
            StaticExecutionArtifactService | None
        ) = None,
        materialization_service: SystemMapMaterializationService | None = None,
        artifact_publisher: BuildArtifactPublisher | None = None,
    ) -> None:
        output_provider = output_artifact_provider or OutputArtifactProvider()
        materializer = (
            materialization_service
            or SystemMapMaterializationService(
                component_detection_service=component_detection_service,
                endpoint_detection_service=endpoint_detection_service,
                risk_hint_service=risk_hint_service,
                flow_derivation_service=flow_derivation_service,
                manual_mapping_service=manual_mapping_service,
                normalize_service=normalize_service,
                validation_service=validation_service,
            )
        )
        publisher = artifact_publisher or BuildArtifactPublisher(
            output_artifact_provider=output_provider,
            markdown_summary_service=markdown_summary_service,
            projection_service=projection_service,
        )
        self._manual_mapping_service = manual_mapping_service
        self._scanner = project_scan_service or ProjectScanService()
        self._output_provider = publisher.output_provider
        self._pipeline = MapBuildPipeline(
            materialization_service=materializer,
            artifact_publisher=publisher,
            canonical_map_loader=canonical_map_loader,
            profile_inference_service=profile_inference_service,
            readiness_report_service=readiness_report_service,
            static_execution_artifact_service=static_execution_artifact_service,
        )

    def build(
        self,
        request: MapBuildRequest,
        *,
        project_id: str | None = None,
        inventory_policy: InventoryPolicyOverlay | None = None,
    ) -> MapBuildResult:
        precondition = self._output_provider.check_preconditions(
            project_path=request.project_path,
            output_dir=request.output,
        )
        project_name = request.project_path.name or "project"
        if not precondition.ok:
            return precondition_error_result(
                output_provider=self._output_provider,
                project_name=project_name,
                error=precondition.error,
                output_run=precondition.output_run,
                warnings=precondition.warnings,
                requested_schema_version=request.system_map_schema_version,
            )
        if (
            precondition.project_root is None
            or precondition.output_run is None
        ):
            raise ValueError("Precondition result is missing resolved paths")
        raw_scan = scan_project(
            self._scanner,
            precondition.project_root,
            inventory_policy=inventory_policy,
        )
        scan_id = f"scan:{uuid4()}"
        build_id = f"build:{uuid4()}"
        lineage = (
            MapBuildLineage(
                project_id=project_id,
                scan_id=scan_id,
                build_id=build_id,
                build_reason="initial_scan",
                generated_at=datetime.now(UTC),
            )
            if project_id is not None
            else None
        )
        return self._pipeline.materialize(
            raw_scan=raw_scan,
            request=request,
            output_run=precondition.output_run,
            project_name=precondition.project_root.name,
            project_root=precondition.project_root,
            project_id=project_id,
            scan_id=scan_id,
            build_id=build_id,
            lineage=lineage,
            warnings=precondition.warnings,
        )

    def build_from_snapshot(
        self,
        snapshot: ScanSnapshot,
        *,
        request: MapBuildRequest,
        output_run: OutputRun,
        build_reason: BuildReason,
        build_id: str | None = None,
        based_on_build_id: str | None = None,
        mapping_ids: tuple[str, ...] = (),
    ) -> MapBuildResult:
        active_build_id = build_id or f"build:{uuid4()}"
        lineage = MapBuildLineage(
            project_id=snapshot.project_id,
            scan_id=snapshot.scan_id,
            build_id=active_build_id,
            based_on_build_id=based_on_build_id,
            build_reason=build_reason,
            applied_mapping_ids=tuple(sorted(mapping_ids)),
            generated_at=datetime.now(UTC),
        )
        return self._pipeline.materialize(
            raw_scan=snapshot.scan_result,
            request=request,
            output_run=output_run,
            project_name=request.project_path.name or "project",
            project_root=request.project_path,
            project_id=snapshot.project_id,
            scan_id=snapshot.scan_id,
            build_id=active_build_id,
            lineage=lineage,
        )

    def build_from_enriched_map(
        self,
        snapshot: ScanSnapshot,
        *,
        system_map: RagSystemMap,
        capability_candidates: tuple[CapabilityCandidateComponent, ...],
        request: MapBuildRequest,
        output_run: OutputRun,
        based_on_build_id: str,
        applied_mapping_ids: tuple[str, ...] = (),
        build_id: str | None = None,
    ) -> MapBuildResult:
        active_build_id = build_id or f"build:{uuid4()}"
        lineage = MapBuildLineage(
            project_id=snapshot.project_id,
            scan_id=snapshot.scan_id,
            build_id=active_build_id,
            based_on_build_id=based_on_build_id,
            build_reason="detail_scan",
            applied_mapping_ids=applied_mapping_ids,
            generated_at=datetime.now(UTC),
        )
        return self._pipeline.materialize_existing_map(
            system_map=system_map,
            capability_candidates=capability_candidates,
            request=request,
            output_run=output_run,
            project_name=request.project_path.name or "project",
            scan_id=snapshot.scan_id,
            build_id=active_build_id,
            lineage=lineage,
            manual_mappings=(
                tuple(
                    self._manual_mapping_service.list_for_project(
                        snapshot.project_id
                    )
                )
                if self._manual_mapping_service is not None
                else ()
            ),
        )
