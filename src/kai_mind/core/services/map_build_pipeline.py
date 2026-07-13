# 這個檔案負責：map build 管線核心——materialize → normalize(v2) → profile →
# readiness → execution artifacts → publish → MapBuildResult。
# 產出 normalized AiSystemMapV2（寫入 MapBuildResult.normalized_ai_system_map）
# 。
#
# 呼叫鏈：
#   MapBuildService.build / build_from_snapshot / build_from_enriched_map
#     → MapBuildPipeline.materialize / materialize_existing_map
#         → SystemMapMaterializationService（組 v1 RagSystemMap）
#         → _complete：
#             CanonicalMapLoader.load → AiSystemMapV2
#             ProfileInferenceService.infer
#             ReadinessReportService.build
#             StaticExecutionArtifactService.build
#             BuildArtifactPublisher.publish
#         → MapBuildResult
from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.analysis_history import MapBuildLineage
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.mapping import ManualMapping
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.services.build_artifact_publisher import (
    BuildArtifactPublisher,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.readiness_report_service import (
    ReadinessReportService,
)
from kai_mind.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)
from kai_mind.core.services.system_map_materialization_service import (
    SystemMapMaterializationService,
)


# 做什麼：編排一次完整 build（從 scan/map 到 artifacts + MapBuildResult）。
# 被誰用：MapBuildService。
# 自己呼叫：materialization、canonical loader、profiles、readiness、execution、
# publisher。
class MapBuildPipeline:
    # 做什麼：注入管線各階段依賴。
    # 被誰呼叫：MapBuildService.__init__。
    # 自己呼叫：預設 CanonicalMapLoader / ProfileInference / Readiness /
    # Execution。
    def __init__(
        self,
        *,
        materialization_service: SystemMapMaterializationService,
        artifact_publisher: BuildArtifactPublisher,
        canonical_map_loader: CanonicalMapLoader | None = None,
        profile_inference_service: ProfileInferenceService | None = None,
        readiness_report_service: ReadinessReportService | None = None,
        static_execution_artifact_service: (
            StaticExecutionArtifactService | None
        ) = None,
    ) -> None:
        self._materialization = materialization_service
        self._publisher = artifact_publisher
        self._canonical_loader = canonical_map_loader or CanonicalMapLoader()
        self._profiles = profile_inference_service or ProfileInferenceService()
        self._readiness = readiness_report_service or ReadinessReportService()
        self._execution = (
            static_execution_artifact_service
            or StaticExecutionArtifactService()
        )

    # 做什麼：從 raw scan materialize 出 v1 map，再走 _complete 產出結果。
    # 被誰呼叫：MapBuildService.build / build_from_snapshot。
    # 自己呼叫：SystemMapMaterializationService.materialize → _complete。
    def materialize(
        self,
        *,
        raw_scan: ProjectScanResult,
        request: MapBuildRequest,
        output_run: OutputRun,
        project_name: str,
        project_root: Path,
        project_id: str | None,
        scan_id: str,
        build_id: str,
        lineage: MapBuildLineage | None,
        warnings: list[str] | None = None,
    ) -> MapBuildResult:
        mapping_ids = (
            lineage.applied_mapping_ids
            if lineage is not None
            and lineage.build_reason == "apply_confirmations"
            else None
        )
        materialized = self._materialization.materialize(
            raw_scan=raw_scan,
            project_name=project_name,
            project_root=project_root,
            request=request,
            project_id=project_id,
            mapping_ids=mapping_ids,
        )
        return self._complete(
            system_map=materialized.system_map,
            capability_candidates=tuple(
                materialized.detection.capability_candidate_components
            ),
            request=request,
            output_run=output_run,
            project_name=project_name,
            scan_id=scan_id,
            build_id=build_id,
            lineage=lineage,
            manual_mappings=materialized.manual_mappings,
            warnings=warnings,
        )

    # 做什麼：已有 v1 map（例如 detail scan 後）直接走 _complete，不再重掃。
    # 被誰呼叫：MapBuildService.build_from_enriched_map。
    # 自己呼叫：_complete。
    def materialize_existing_map(
        self,
        *,
        system_map: RagSystemMap,
        capability_candidates: tuple[CapabilityCandidateComponent, ...],
        request: MapBuildRequest,
        output_run: OutputRun,
        project_name: str,
        scan_id: str,
        build_id: str,
        lineage: MapBuildLineage,
        manual_mappings: tuple[ManualMapping, ...] = (),
    ) -> MapBuildResult:
        return self._complete(
            system_map=system_map,
            capability_candidates=capability_candidates,
            request=request,
            output_run=output_run,
            project_name=project_name,
            scan_id=scan_id,
            build_id=build_id,
            lineage=lineage,
            manual_mappings=manual_mappings,
        )

    # 做什麼：管線後半段——normalize v2、profile、readiness、execution、
    # publish。
    # 被誰呼叫：materialize / materialize_existing_map。
    # 自己呼叫：
    #   CanonicalMapLoader.load → 填 scan_id/build_id
    #   ProfileInferenceService.infer
    #   ReadinessReportService.build
    #   StaticExecutionArtifactService.build
    #   BuildArtifactPublisher.publish
    # → 組 MapBuildResult（含 normalized_ai_system_map）。
    def _complete(
        self,
        *,
        system_map: RagSystemMap,
        capability_candidates: tuple[CapabilityCandidateComponent, ...],
        request: MapBuildRequest,
        output_run: OutputRun,
        project_name: str,
        scan_id: str,
        build_id: str,
        lineage: MapBuildLineage | None,
        manual_mappings: tuple[ManualMapping, ...] = (),
        warnings: list[str] | None = None,
    ) -> MapBuildResult:
        load_result = self._canonical_loader.load(
            system_map.model_dump(mode="json")
        )
        normalized = load_result.normalized.model_copy(
            update={
                "scan_id": scan_id,
                "build_id": build_id,
                "generated_from_build_id": build_id,
            }
        )
        profiles = self._profiles.infer(
            normalized,
            build_id=build_id,
            scan_id=scan_id,
            environment_id=normalized.environment_id,
            capability_candidate_components=capability_candidates,
        )
        readiness = self._readiness.build(
            system_map=normalized,
            profile_result=profiles,
        )
        execution = self._execution.build(
            normalized,
            manual_mappings=manual_mappings,
        )
        published = self._publisher.publish(
            system_map=system_map,
            normalized_system_map=normalized,
            profile_result=profiles,
            readiness_report=readiness,
            execution=execution,
            output_run=output_run,
        )
        migration_warnings = list(load_result.migration_warnings)
        if request.system_map_schema_version == "ai-system-map/v2":
            migration_warnings.append(
                "requested_v2_opt_in_but_active_output_remains_v1_until_plan_13"
            )
        return MapBuildResult(
            status="ok",
            project_name=project_name,
            output_run_dir=output_run.root_dir,
            map_json_path=published.map_json_path,
            map_markdown_path=published.map_markdown_path,
            profile_signals_path=published.profile_signals_path,
            readiness_report_path=published.readiness_report_path,
            call_graph_path=published.call_graph_path,
            dataflow_hints_path=published.dataflow_hints_path,
            execution_paths_path=published.execution_paths_path,
            evidence_table_path=published.evidence_table_path,
            system_map_mermaid_path=published.system_map_mermaid_path,
            execution_map_mermaid_path=published.execution_map_mermaid_path,
            viewer_load_result=published.viewer_load_result,
            ai_system_map=system_map,
            normalized_ai_system_map=normalized,
            profile_inference_result=profiles,
            readiness_report=readiness,
            lineage=lineage,
            active_schema_version="ai-system-map/v1",
            requested_schema_version=request.system_map_schema_version,
            migration_warnings=migration_warnings,
            warnings=list(warnings or ()),
        )
