from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from importlib.util import find_spec
from pathlib import Path
from typing import Final

import pytest

from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.scan import OutputRun, ProjectScanResult
from systograph.core.services.map_build_pipeline import MapBuildPipeline
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationService,
)

# Modules that existed only to write the operator rollback v1 artifact.
# Refactor 06 deleted them; the build path must never grow them back.
REMOVED_ROLLBACK_MODULES: Final[tuple[str, ...]] = (
    "systograph.core.services.legacy_v1_rollback_service",
    "systograph.core.services.system_map_materialization_service",
    "systograph.core.services.system_map_normalize_service",
)


@pytest.mark.parametrize("module_name", REMOVED_ROLLBACK_MODULES)
def test_rollback_writer_modules_no_longer_exist(module_name: str) -> None:
    """The v1 writer graph is gone, not merely unreferenced.

    Given a module that only the operator rollback writer needed,
    When the import system is asked to locate it,
    Then nothing is found, so no caller can reach a v1 writer.
    """
    assert find_spec(module_name) is None


def test_build_wiring_exposes_no_v1_output_seam() -> None:
    """No injection point survives the removed write path.

    Given the build service and the build pipeline constructors,
    When their parameters are inspected,
    Then neither accepts a rollback writer nor a canonical output
    version, so the v1 output mode cannot be reintroduced through
    dependency injection and no caller can label an artifact it did not
    produce.
    """
    # Given / When
    parameters = set(
        inspect.signature(MapBuildService.__init__).parameters
    ) | set(inspect.signature(MapBuildPipeline.__init__).parameters)

    # Then
    assert not [
        name
        for name in parameters
        if "rollback" in name or "canonical_output_version" in name
    ]


def test_published_artifact_and_reported_version_cannot_disagree(
    tmp_path: Path,
) -> None:
    """The reported schema version is the artifact's, not a caller's.

    Given a build with no way to select an output version,
    When a snapshot is materialized,
    Then active_schema_version equals the schema_version actually
    written to disk — the v1 label is unreachable.
    """
    # Given
    snapshot = ScanSnapshot(
        project_id="project:single-truth",
        scan_id="scan:single-truth",
        generated_at=datetime(2026, 8, 7, tzinfo=UTC),
        inventory_digest="sha256:single-truth",
        scan_result=ProjectScanResult(),
    )

    # When
    result = MapBuildService().build_from_snapshot(
        snapshot,
        request=MapBuildRequest(project_path=tmp_path / "project"),
        output_run=OutputRun(root_dir=tmp_path / "build"),
        build_reason="initial_scan",
        build_id="build:single-truth",
    )

    # Then
    assert result.map_json_path is not None
    artifact = json.loads(result.map_json_path.read_text(encoding="utf-8"))
    assert result.active_schema_version == artifact["schema_version"]
    assert result.active_schema_version == "ai-system-map/v2"


def test_default_service_materializes_through_the_v2_writer_only() -> None:
    """One build path, one materializer.

    Given a default MapBuildService,
    When its pipeline is inspected,
    Then the only materializer wired in is the active v2 writer.
    """
    # Given / When
    service = MapBuildService()

    # Then
    assert isinstance(
        service._pipeline._materialization,
        SystemMapV2MaterializationService,
    )
