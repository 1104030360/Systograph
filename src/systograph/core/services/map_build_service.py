# 這個檔案負責：map build 對外服務（CLI / Web / Apply / DetailScan 的入口）。
# 組裝依賴、檢查 precondition、掃專案，再委派 MapBuildPipeline。
#
# 呼叫鏈：
#   CLI map_command / Web scan_routes / ApplyConfirmations / DetailScanBuild
#     → MapBuildService.build / build_from_snapshot / build_from_enriched_map
#         → OutputArtifactProvider.check_preconditions
#         → scan_project（僅 build）
#         → MapBuildPipeline.materialize / materialize_existing_map
#         → MapBuildResult
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.analysis_history import (
    BuildReason,
    MapBuildLineage,
    ScanSnapshot,
)
from systograph.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.scan import OutputRun
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from systograph.core.services.build_artifact_publisher import (
    BuildArtifactPublisher,
)
from systograph.core.services.canonical_output_configuration import (
    canonical_output_version_from_env,
    require_public_v2_selection,
)
from systograph.core.services.component_detection_service import (
    ComponentDetectionService,
)
from systograph.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from systograph.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from systograph.core.services.graph_markdown_renderer import (
    GraphMarkdownRenderer,
)
from systograph.core.services.graph_mermaid_renderer import (
    GraphMermaidRenderer,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.map_build_orchestration import (
    precondition_error_result,
    scan_project,
)
from systograph.core.services.map_build_pipeline import MapBuildPipeline
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from systograph.core.services.readiness_report_service import (
    ReadinessReportService,
)
from systograph.core.services.risk_hint_service import RiskHintService
from systograph.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)
from systograph.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationService,
)
from systograph.core.services.system_map_v2_normalize_service import (
    SystemMapV2NormalizeService,
)
from systograph.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)
from systograph.core.services.viewer_session_service import (
    ViewerSessionService,
)


# 做什麼：對外 build facade；組 pipeline，提供三種建圖入口。
# 被誰用：CLI、Web、ApplyConfirmations、DetailScanBuild。
# 自己呼叫：MapBuildPipeline、scan_project、precondition_error_result。
class MapBuildService:
    # 做什麼：組裝 materializer / publisher / pipeline 依賴圖。
    # 被誰呼叫：app 啟動或測試注入。
    # 自己呼叫：SystemMapV2MaterializationService、BuildArtifactPublisher、
    # MapBuildPipeline。
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
        normalize_service: SystemMapV2NormalizeService | None = None,
        graph_markdown_renderer: GraphMarkdownRenderer | None = None,
        graph_mermaid_renderer: GraphMermaidRenderer | None = None,
        projection_service: ViewerSessionService | None = None,
        validation_service: SystemMapV2ValidationService | None = None,
        profile_inference_service: ProfileInferenceService | None = None,
        readiness_report_service: ReadinessReportService | None = None,
        static_execution_artifact_service: (
            StaticExecutionArtifactService | None
        ) = None,
        materialization_service: SystemMapV2MaterializationService
        | None = None,
        artifact_publisher: BuildArtifactPublisher | None = None,
    ) -> None:
        output_provider = output_artifact_provider or OutputArtifactProvider()
        materializer = (
            materialization_service
            or SystemMapV2MaterializationService(
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
            markdown_renderer=graph_markdown_renderer,
            mermaid_renderer=graph_mermaid_renderer,
            projection_service=projection_service,
        )
        # Guard, not a value source: refuse to build under a misconfigured
        # SYSTOGRAPH_CANONICAL_OUTPUT_VERSION. The return value is
        # deliberately discarded — the output version is not selectable,
        # so the pipeline reads it from the v2 constant instead. This keeps
        # the fail-fast on every entry point that builds, including the CLI,
        # which has no other startup hook.
        canonical_output_version_from_env()
        self._manual_mapping_service = manual_mapping_service
        self._scanner = project_scan_service or ProjectScanService()
        self._output_provider = publisher.output_provider
        self._pipeline = MapBuildPipeline(
            materialization_service=materializer,
            artifact_publisher=publisher,
            profile_inference_service=profile_inference_service,
            readiness_report_service=readiness_report_service,
            static_execution_artifact_service=static_execution_artifact_service,
        )

    # 做什麼：完整初掃 build——precondition → scan → pipeline.materialize。
    # 被誰呼叫：CLI map（唯一 production caller）。
    # 自己呼叫：check_preconditions、scan_project、
    # MapBuildPipeline.materialize。
    # 失敗 precondition：回 precondition_error_result（status=error）。
    def build(
        self,
        request: MapBuildRequest,
        *,
        project_id: str | None = None,
        inventory_policy: InventoryPolicyOverlay | None = None,
    ) -> MapBuildResult:
        require_public_v2_selection(request.system_map_schema_version)
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

    # 做什麼：用既有 ScanSnapshot 重建（不重掃 filesystem inventory）。
    # 被誰呼叫：Web POST /api/scans、ApplyConfirmations。
    # 自己呼叫：組 MapBuildLineage → MapBuildPipeline.materialize。
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
        require_public_v2_selection(request.system_map_schema_version)
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

    # 做什麼：用已 enrich 的 v1 map（如 detail scan 後）直接 publish，不重跑
    # detection。
    # 被誰呼叫：DetailScanBuild 相關流程。
    # 自己呼叫：manual_mapping_service.list_for_project →
    #           MapBuildPipeline.materialize_existing_map。
    def build_from_enriched_map(
        self,
        snapshot: ScanSnapshot,
        *,
        system_map: AiSystemMapV2,
        capability_candidates: tuple[CapabilityCandidateComponent, ...],
        request: MapBuildRequest,
        output_run: OutputRun,
        based_on_build_id: str,
        applied_mapping_ids: tuple[str, ...] = (),
        build_id: str | None = None,
    ) -> MapBuildResult:
        require_public_v2_selection(request.system_map_schema_version)
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
