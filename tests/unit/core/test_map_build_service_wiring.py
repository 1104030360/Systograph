from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalProject,
)
from kai_mind.core.models.analysis_history import MapBuildLineage
from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.services.build_artifact_publisher import (
    BuildArtifactPublisher,
)
from kai_mind.core.services.legacy_v1_rollback_service import (
    LegacyV1RollbackError,
    LegacyV1RollbackService,
)
from kai_mind.core.services.map_build_pipeline import MapBuildPipeline
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.system_map_materialization_service import (
    SystemMapMaterializationService,
)
from kai_mind.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationService,
)

# Modules that only the operator rollback writer needs. Plan 15 deletes
# them, so the active v2 build path must never reach them.
ROLLBACK_MODULES: Final[tuple[str, ...]] = (
    "kai_mind.core.services.legacy_v1_rollback_service",
    "kai_mind.core.services.system_map_materialization_service",
    "kai_mind.core.services.system_map_normalize_service",
)

# Import purity is only observable in a fresh interpreter: an in-process
# probe would see modules that unrelated earlier tests already imported.
_PROBE_SOURCE: Final[str] = f"""
import json
import sys

from kai_mind.core.services.map_build_service import MapBuildService

MapBuildService()
targets = {json.dumps(list(ROLLBACK_MODULES))}
print(json.dumps(sorted(set(targets) & set(sys.modules))))
"""


def _rollback_modules_loaded_by(canonical_output_version: str) -> set[str]:
    env = dict(os.environ)
    env["KAI_MIND_CANONICAL_OUTPUT_VERSION"] = canonical_output_version
    probe = subprocess.run(
        [sys.executable, "-c", _PROBE_SOURCE],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    loaded: list[str] = json.loads(probe.stdout)
    return set(loaded)


def _rollback_stub() -> LegacyV1RollbackService:
    return LegacyV1RollbackService(
        materialization_service=SystemMapMaterializationService()
    )


def _writerless_v1_pipeline() -> MapBuildPipeline:
    return MapBuildPipeline(
        materialization_service=SystemMapV2MaterializationService(),
        artifact_publisher=BuildArtifactPublisher(),
        canonical_output_version="ai-system-map/v1",
        legacy_v1_rollback_service=None,
    )


def test_default_v2_service_imports_no_v1_rollback_module() -> None:
    """The default build path must not touch the rollback object graph.

    Given a fresh interpreter running the active ai-system-map/v2 mode,
    When MapBuildService is constructed with no injected dependencies,
    Then none of the operator rollback modules are imported, so Plan 15
    can delete them without breaking the active path.
    """
    assert _rollback_modules_loaded_by("ai-system-map/v2") == set()


def test_operator_v1_env_loads_the_rollback_modules() -> None:
    """Operator rollback still builds its writer graph eagerly.

    Given a fresh interpreter with the operator rollback env set to v1,
    When MapBuildService is constructed with no injected dependencies,
    Then the rollback modules are imported so the v1 writer exists.
    """
    assert _rollback_modules_loaded_by("ai-system-map/v1") == set(
        ROLLBACK_MODULES
    )


def test_v2_service_leaves_the_pipeline_rollback_writer_unset() -> None:
    """v2 mode holds no rollback writer instance.

    Given the active ai-system-map/v2 mode,
    When MapBuildService is constructed,
    Then the pipeline keeps its rollback writer unset and relies on the
    legacy_rollback_writer_unavailable guard.
    """
    service = MapBuildService(canonical_output_version="ai-system-map/v2")

    assert service._pipeline._legacy_rollback is None


def test_v1_service_builds_the_rollback_writer() -> None:
    """v1 mode still wires a rollback writer into the pipeline.

    Given the operator rollback ai-system-map/v1 mode,
    When MapBuildService is constructed with no injected writer,
    Then the pipeline holds a rollback writer instance.
    """
    service = MapBuildService(canonical_output_version="ai-system-map/v1")

    assert isinstance(
        service._pipeline._legacy_rollback, LegacyV1RollbackService
    )


def test_injected_rollback_writer_wins_in_v2_mode() -> None:
    """The DI parameter survives the lazy construction rewrite.

    Given an explicitly injected rollback writer,
    When MapBuildService is constructed in the active v2 mode,
    Then the pipeline holds exactly that instance.
    """
    injected = _rollback_stub()

    service = MapBuildService(
        canonical_output_version="ai-system-map/v2",
        legacy_v1_rollback_service=injected,
    )

    assert service._pipeline._legacy_rollback is injected


def test_injected_rollback_writer_wins_in_v1_mode() -> None:
    """Injection is never overwritten by the lazily built writer.

    Given an explicitly injected rollback writer,
    When MapBuildService is constructed in operator rollback v1 mode,
    Then the pipeline holds exactly that instance.
    """
    injected = _rollback_stub()

    service = MapBuildService(
        canonical_output_version="ai-system-map/v1",
        legacy_v1_rollback_service=injected,
    )

    assert service._pipeline._legacy_rollback is injected


def test_materialize_fails_closed_without_a_rollback_writer(
    tmp_path: Path,
) -> None:
    """An unset rollback writer never degrades into a v2 build.

    Given a pipeline in operator rollback mode with no rollback writer,
    When a scan is materialized,
    Then it fails closed with legacy_rollback_writer_unavailable and
    writes nothing, which is what makes the v2-mode None safe.
    """
    output_dir = tmp_path / "build"

    with pytest.raises(
        LegacyV1RollbackError,
        match="legacy_rollback_writer_unavailable",
    ):
        _writerless_v1_pipeline().materialize(
            raw_scan=ProjectScanResult(),
            request=MapBuildRequest(project_path=tmp_path / "project"),
            output_run=OutputRun(root_dir=output_dir),
            project_name="project",
            project_root=tmp_path / "project",
            project_id=None,
            scan_id="scan:writerless",
            build_id="build:writerless",
            lineage=None,
        )

    assert not output_dir.exists()


def test_existing_map_publish_fails_closed_without_a_rollback_writer(
    tmp_path: Path,
) -> None:
    """The enriched-map entry point applies the same fail-closed guard.

    Given a pipeline in operator rollback mode with no rollback writer,
    When an already enriched map is published,
    Then it fails closed with legacy_rollback_writer_unavailable and
    writes nothing.
    """
    output_dir = tmp_path / "build"

    with pytest.raises(
        LegacyV1RollbackError,
        match="legacy_rollback_writer_unavailable",
    ):
        _writerless_v1_pipeline().materialize_existing_map(
            system_map=AiSystemMapV2(
                schema_version="ai-system-map/v2",
                system_type="ai_system",
                project=CanonicalProject(name="project"),
            ),
            capability_candidates=(),
            request=MapBuildRequest(project_path=tmp_path / "project"),
            output_run=OutputRun(root_dir=output_dir),
            project_name="project",
            scan_id="scan:writerless",
            build_id="build:writerless",
            lineage=MapBuildLineage(
                project_id="project:writerless",
                scan_id="scan:writerless",
                build_id="build:writerless",
                based_on_build_id="build:parent",
                build_reason="detail_scan",
                generated_at=datetime(2026, 7, 28, tzinfo=UTC),
            ),
        )

    assert not output_dir.exists()
