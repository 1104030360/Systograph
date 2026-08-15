from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from systograph.core.models.analysis_history import ProjectState, ScanSnapshot
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from systograph.core.services.canonical_output_configuration import (
    require_public_v2_selection,
)
from systograph.core.services.map_build_orchestration import (
    precondition_error_result,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.noninteractive_inventory_gate import (
    NonInteractiveInventoryGate,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.scan_snapshot_service import ScanSnapshotService
from systograph.core.services.ua_parity_service import UaParityService
from systograph.core.services.ua_structural_adapter import UaStructuralAdapter
from systograph.core.services.understand_anything_analysis_service import (
    UnderstandAnythingAnalysisService,
)


@dataclass(frozen=True, slots=True)
class CliMapWorkflowResult:
    build: MapBuildResult
    snapshot: ScanSnapshot | None


class CliMapWorkflow:
    def __init__(
        self,
        *,
        state_dir: Path,
        output_provider: OutputArtifactProvider | None = None,
        repository: LocalJsonStateProvider | None = None,
        scanner: ProjectScanService | None = None,
        inventory_gate: NonInteractiveInventoryGate | None = None,
        snapshot_service: ScanSnapshotService | None = None,
        map_build_service: MapBuildService | None = None,
    ) -> None:
        self._output = output_provider or OutputArtifactProvider()
        self._repository = repository or LocalJsonStateProvider(state_dir)
        self._scanner = scanner or ProjectScanService()
        self._inventory_gate = inventory_gate or NonInteractiveInventoryGate()
        self._snapshot_service = snapshot_service or ScanSnapshotService(
            project_scan_service=self._scanner,
            repository=self._repository,
            ua_analysis_service=UnderstandAnythingAnalysisService(),
            ua_adapter=UaStructuralAdapter(),
            ua_parity_service=UaParityService(),
        )
        self._map_build = map_build_service or MapBuildService(
            project_scan_service=self._scanner,
            output_artifact_provider=self._output,
        )

    def build(self, request: MapBuildRequest) -> CliMapWorkflowResult:
        require_public_v2_selection(request.system_map_schema_version)
        precondition = self._output.check_preconditions(
            project_path=request.project_path,
            output_dir=request.output,
        )
        project_name = request.project_path.name or "project"
        if not precondition.ok:
            return CliMapWorkflowResult(
                build=precondition_error_result(
                    output_provider=self._output,
                    project_name=project_name,
                    error=precondition.error,
                    output_run=precondition.output_run,
                    warnings=precondition.warnings,
                    requested_schema_version=request.system_map_schema_version,
                ),
                snapshot=None,
            )
        if (
            precondition.project_root is None
            or precondition.output_run is None
        ):
            raise ValueError("Precondition result is missing resolved paths")
        project = self._project(precondition.project_root)
        inventory = self._inventory_gate.select(
            project_id=project.project_id,
            project_root=precondition.project_root,
        )
        snapshot = self._snapshot_service.scan_and_save(
            project_id=project.project_id,
            project_root=precondition.project_root,
            inventory=inventory,
        )
        result = self._map_build.build_from_snapshot(
            snapshot,
            request=request.model_copy(
                update={"project_path": precondition.project_root}
            ),
            output_run=precondition.output_run,
            build_reason="initial_scan",
        )
        return CliMapWorkflowResult(build=result, snapshot=snapshot)

    def _project(self, project_root: Path) -> ProjectState:
        digest = (
            "sha256:"
            + hashlib.sha256(str(project_root).encode("utf-8")).hexdigest()
        )
        existing = self._repository.find_project_by_path_digest(digest)
        if existing is not None:
            return existing
        return self._repository.save_project(
            ProjectState(
                project_id=f"project:{uuid4()}",
                project_name=project_root.name or "project",
                source_type="local_path",
                canonical_path=str(project_root),
                path_digest=digest,
                created_at=datetime.now(UTC),
            )
        )
