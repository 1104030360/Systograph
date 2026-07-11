from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from kai_mind.core.models.analysis_history import (
    LatestBuildPointer,
    ScanSnapshot,
)
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.scan import OutputRun
from kai_mind.core.models.system_map import DetailScanResult, ScanDepth
from kai_mind.core.providers.local_json_state_errors import StateConflictError
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.map_build_query_service import MapBuildQueryService
from kai_mind.core.services.map_build_service import MapBuildService


class DetailBuildRepository(Protocol):
    def get_latest_pointer(
        self, project_id: str
    ) -> LatestBuildPointer | None: ...

    def get_snapshot(
        self, project_id: str, scan_id: str
    ) -> ScanSnapshot | None: ...

    def promote_latest_build(
        self,
        *,
        project_id: str,
        build_id: str,
        expected_latest_build_id: str | None,
        expected_revision: int,
    ) -> LatestBuildPointer: ...

    def discard_unpublished_build(
        self, project_id: str, build_id: str
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class DetailScanBuildResult:
    detail_scan: DetailScanResult
    source_build_id: str
    build_result: MapBuildResult
    warnings: tuple[str, ...] = ()


class DetailScanBuildError(RuntimeError):
    pass


class DetailScanBuildService:
    def __init__(
        self,
        *,
        detail_scan_service: DetailScanService,
        map_build_service: MapBuildService,
        query_service: MapBuildQueryService,
        manifest_service: BuildManifestService,
        repository: DetailBuildRepository,
    ) -> None:
        self._detail_scan = detail_scan_service
        self._map_build = map_build_service
        self._query = query_service
        self._manifest = manifest_service
        self._repository = repository

    def run(
        self,
        *,
        project_id: str,
        project_root: Path,
        build_id: str | None,
        target_type: str,
        target: str,
        scan_depth: ScanDepth,
    ) -> DetailScanBuildResult:
        warnings = () if build_id else ("latest_build_fallback",)
        base = (
            self._query.get(build_id)
            if build_id is not None
            else self._query.latest(project_id)
        )
        lineage = base.lineage
        if lineage is None or lineage.project_id != project_id:
            raise DetailScanBuildError("project_build_mismatch")
        latest = self._repository.get_latest_pointer(project_id)
        if latest is None or latest.latest_build_id != lineage.build_id:
            raise DetailScanBuildError("base_build_not_latest")
        snapshot = self._repository.get_snapshot(project_id, lineage.scan_id)
        if snapshot is None or base.ai_system_map is None:
            raise DetailScanBuildError("scan_snapshot_missing")
        if base.profile_inference_result is None:
            raise DetailScanBuildError("profile_sidecar_unavailable")
        enriched = self._detail_scan.scan(
            project_root=project_root,
            system_map=base.ai_system_map,
            target_type=target_type,
            target=target,
            scan_depth=scan_depth,
            expected_file_fingerprints=snapshot.file_fingerprints,
        )
        child_build_id = f"build:{uuid4()}"
        output_root = Path(base.output_run_dir or "outputs").parent
        output_dir = output_root / child_build_id.replace(":", "_")
        candidates = (
            base.profile_inference_result.capability_candidate_components
        )
        try:
            child = self._map_build.build_from_enriched_map(
                snapshot,
                system_map=enriched.system_map,
                capability_candidates=tuple(candidates),
                request=MapBuildRequest(
                    project_path=project_root,
                    output=output_root,
                    system_map_schema_version=base.requested_schema_version,
                ),
                output_run=OutputRun(root_dir=output_dir),
                based_on_build_id=lineage.build_id,
                applied_mapping_ids=lineage.applied_mapping_ids,
                build_id=child_build_id,
            )
            self._manifest.persist(child)
            self._repository.promote_latest_build(
                project_id=project_id,
                build_id=child_build_id,
                expected_latest_build_id=lineage.build_id,
                expected_revision=latest.revision,
            )
        except StateConflictError as exc:
            self._cleanup(project_id, child_build_id, output_dir)
            raise DetailScanBuildError("base_build_not_latest") from exc
        except Exception:
            self._cleanup(project_id, child_build_id, output_dir)
            raise
        return DetailScanBuildResult(
            detail_scan=enriched.detail_scan,
            source_build_id=lineage.build_id,
            build_result=child,
            warnings=warnings,
        )

    def _cleanup(
        self,
        project_id: str,
        build_id: str,
        output_dir: Path,
    ) -> None:
        try:
            self._repository.discard_unpublished_build(project_id, build_id)
        except StateConflictError:
            return
        if output_dir.is_dir():
            shutil.rmtree(output_dir)
