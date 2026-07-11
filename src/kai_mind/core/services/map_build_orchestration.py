from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.map_build import (
    MapBuildResult,
    SystemMapSchemaSelection,
)
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)


def scan_project(
    scanner: ProjectScanService,
    project_root: Path,
    *,
    inventory_policy: InventoryPolicyOverlay | None,
) -> ProjectScanResult:
    if inventory_policy is None:
        return scanner.scan(project_root)
    return scanner.scan(project_root, inventory_policy=inventory_policy)


def precondition_error_result(
    *,
    output_provider: OutputArtifactProvider,
    project_name: str,
    error: PreconditionError | None,
    output_run: OutputRun | None,
    warnings: list[str],
    requested_schema_version: SystemMapSchemaSelection,
) -> MapBuildResult:
    map_error_path = None
    if error is not None and output_run is not None:
        map_error_path = output_provider.write_map_error(
            error,
            output_run=output_run,
        )
    return MapBuildResult(
        status="error",
        project_name=project_name,
        output_run_dir=output_run.root_dir if output_run else None,
        map_error_path=map_error_path,
        requested_schema_version=requested_schema_version,
        warnings=warnings,
        error=error,
    )
