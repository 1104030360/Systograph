# 這個檔案負責：map build 管線核心——materialize(v2) → profile →
# readiness → execution artifacts → publish → MapBuildResult。
# 產出唯一 normalized AiSystemMapV2（寫入 MapBuildResult.ai_system_map）。
#
# 呼叫鏈：
#   MapBuildService.build / build_from_snapshot / build_from_enriched_map
#     → MapBuildPipeline.materialize / materialize_existing_map
#         → SystemMapV2MaterializationService（normal path 直接組 v2）
#         → _complete：
#             ProfileInferenceService.infer
#             ReadinessReportService.build
#             StaticExecutionArtifactService.build
#             BuildArtifactPublisher.publish
#         → MapBuildResult
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.analysis_history import MapBuildLineage
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.map_build import (
    MapBuildRequest,
    MapBuildResult,
    SystemMapSchemaSelection,
)
from kai_mind.core.models.mapping import ManualMapping
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.services.build_artifact_publisher import (
    BuildArtifactPublisher,
)
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.readiness_report_service import (
    ReadinessReportService,
)
from kai_mind.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)
from kai_mind.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationService,
)

if TYPE_CHECKING:
    from kai_mind.core.services.legacy_v1_rollback_service import (
        LegacyV1RollbackService,
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
        materialization_service: SystemMapV2MaterializationService,
        artifact_publisher: BuildArtifactPublisher,
        canonical_output_version: SystemMapSchemaSelection,
        legacy_v1_rollback_service: LegacyV1RollbackService | None = None,
        profile_inference_service: ProfileInferenceService | None = None,
        readiness_report_service: ReadinessReportService | None = None,
        static_execution_artifact_service: (
            StaticExecutionArtifactService | None
        ) = None,
    ) -> None:
        self._materialization = materialization_service
        self._publisher = artifact_publisher
        self._canonical_output_version = canonical_output_version
        self._legacy_rollback = legacy_v1_rollback_service
        self._profiles = profile_inference_service or ProfileInferenceService()
        self._readiness = readiness_report_service or ReadinessReportService()
        self._execution = (
            static_execution_artifact_service
            or StaticExecutionArtifactService()
        )

    # 做什麼：normal mode 從 raw scan 直接 materialize v2；operator rollback
    # mode 才由隔離 writer 產出 v1 artifact 並立即 normalize，再走 _complete。
    # 被誰呼叫：MapBuildService.build / build_from_snapshot。
    # 自己呼叫：SystemMapV2MaterializationService.materialize 或
    # LegacyV1RollbackService.materialize → _complete。
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
        artifact_map: BaseModel | None = None
        # Census contract: every "ai-system-map/v1" literal in this file is
        # what tests/contracts/test_v2_cutover_consumer_allowlist.py finds by
        # AST scan, so they must stay inline string literals. Folding them
        # into a shared constant would silently drop this file from the
        # census, not clean it up.
        if self._canonical_output_version == "ai-system-map/v1":
            # Operator rollback only: keep the v1 writer contract out of
            # the active v2 import graph.
            from kai_mind.core.services.legacy_v1_rollback_service import (
                LegacyV1RollbackError,
            )

            if self._legacy_rollback is None:
                raise LegacyV1RollbackError(
                    "legacy_rollback_writer_unavailable"
                )
            rollback = self._legacy_rollback.materialize(
                raw_scan=raw_scan,
                project_name=project_name,
                project_root=project_root,
                request=request,
                project_id=project_id,
                mapping_ids=mapping_ids,
            )
            system_map = rollback.normalized_map
            detection = rollback.detection
            manual_mappings = rollback.manual_mappings
            artifact_map = rollback.artifact_map
        else:
            materialized = self._materialization.materialize(
                raw_scan=raw_scan,
                project_name=project_name,
                project_root=project_root,
                request=request,
                project_id=project_id,
                mapping_ids=mapping_ids,
            )
            system_map = materialized.system_map
            detection = materialized.detection
            manual_mappings = materialized.manual_mappings
        return self._complete(
            system_map=system_map,
            artifact_map=artifact_map,
            capability_candidates=tuple(
                detection.capability_candidate_components
            ),
            request=request,
            output_run=output_run,
            project_name=project_name,
            scan_id=scan_id,
            build_id=build_id,
            lineage=lineage,
            manual_mappings=manual_mappings,
            warnings=warnings,
        )

    # 做什麼：已有 v2 map（例如 detail scan 後）直接走 _complete，不再重掃。
    # 被誰呼叫：MapBuildService.build_from_enriched_map。
    # 自己呼叫：_complete。
    def materialize_existing_map(
        self,
        *,
        system_map: AiSystemMapV2,
        capability_candidates: tuple[CapabilityCandidateComponent, ...],
        request: MapBuildRequest,
        output_run: OutputRun,
        project_name: str,
        scan_id: str,
        build_id: str,
        lineage: MapBuildLineage,
        manual_mappings: tuple[ManualMapping, ...] = (),
    ) -> MapBuildResult:
        if self._canonical_output_version == "ai-system-map/v1":
            # Operator rollback only: keep the v1 writer contract out of
            # the active v2 import graph.
            from kai_mind.core.services.legacy_v1_rollback_service import (
                LegacyV1RollbackError,
            )

            if self._legacy_rollback is None:
                raise LegacyV1RollbackError(
                    "legacy_rollback_writer_unavailable"
                )
            # Preflight first: an unrepresentable map earns the more
            # specific legacy_rollback_not_representable. Only then comes
            # the honest refusal — the rollback writer rebuilds from a raw
            # scan, never from an already enriched map.
            self._legacy_rollback.require_representable(system_map)
            raise LegacyV1RollbackError(
                "legacy_rollback_detail_scan_unsupported"
            )
        return self._complete(
            system_map=system_map,
            artifact_map=None,
            capability_candidates=capability_candidates,
            request=request,
            output_run=output_run,
            project_name=project_name,
            scan_id=scan_id,
            build_id=build_id,
            lineage=lineage,
            manual_mappings=manual_mappings,
        )

    # 做什麼：完成固定 scope 的 v2、profile、readiness、execution 與 publish。
    # 被誰呼叫：materialize / materialize_existing_map。
    # 自己呼叫：
    #   填 scan_id/build_id → ProfileInferenceService.infer
    #   ReadinessReportService.build
    #   StaticExecutionArtifactService.build
    #   BuildArtifactPublisher.publish
    # → 組 MapBuildResult（ai_system_map 是唯一 canonical v2 field）。
    def _complete(
        self,
        *,
        system_map: AiSystemMapV2,
        artifact_map: BaseModel | None,
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
        normalized = system_map.model_copy(
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
            system_map=normalized,
            artifact_map=artifact_map,
            profile_result=profiles,
            readiness_report=readiness,
            execution=execution,
            output_run=output_run,
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
            ai_system_map=normalized,
            profile_inference_result=profiles,
            readiness_report=readiness,
            lineage=lineage,
            active_schema_version=self._canonical_output_version,
            requested_schema_version=request.system_map_schema_version,
            source_schema_version=(
                normalized.source_schema_version or normalized.schema_version
            ),
            operator_rollback_active=(
                self._canonical_output_version == "ai-system-map/v1"
            ),
            migration_warnings=list(normalized.migration_warnings),
            warnings=list(warnings or ()),
        )
