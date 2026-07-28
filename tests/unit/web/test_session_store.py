"""Unit tests for the web session store implementations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from kai_mind.core.models.analysis_history import ScanSnapshot
from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.session_store import PersistentSessionStore


class StoreFixture(NamedTuple):
    """One session store plus two published builds on disk."""

    store: PersistentSessionStore
    older_project_id: str
    newer_project_id: str
    older_map_json: Path
    newer_map_json: Path


def _publish_build(
    store: PersistentSessionStore,
    repository: LocalJsonStateProvider,
    manifest_service: BuildManifestService,
    *,
    workspace: Path,
    build_id: str,
    scan_id: str,
) -> tuple[str, Path]:
    """Publish one real build (artifacts + manifest + latest pointer)."""
    workspace.mkdir(parents=True, exist_ok=True)
    project = store.import_project(
        project_path=workspace,
        source_type="local_path",
    )
    snapshot = ScanSnapshot(
        project_id=project.project_id,
        scan_id=scan_id,
        generated_at=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(),
    )
    result = MapBuildService().build_from_snapshot(
        snapshot,
        request=MapBuildRequest(project_path=project.project_path),
        output_run=OutputRun(root_dir=workspace / "output"),
        build_id=build_id,
        build_reason="initial_scan",
    )
    manifest_service.persist(result)
    repository.promote_latest_build(
        project_id=project.project_id,
        build_id=build_id,
        expected_latest_build_id=None,
        expected_revision=0,
    )
    assert result.map_json_path is not None
    return project.project_id, result.map_json_path


def _store_with_two_builds(tmp_path: Path) -> StoreFixture:
    """Two projects, each with one published build; the second is newest."""
    repository = LocalJsonStateProvider(tmp_path / "state")
    manifest_service = BuildManifestService(repository=repository)
    store = PersistentSessionStore(
        repository=repository,
        manifest_service=manifest_service,
        projection_service=ViewerSessionService(),
    )
    older_id, older_map = _publish_build(
        store,
        repository,
        manifest_service,
        workspace=tmp_path / "older",
        build_id="build:first",
        scan_id="scan:first",
    )
    newer_id, newer_map = _publish_build(
        store,
        repository,
        manifest_service,
        workspace=tmp_path / "newer",
        build_id="build:second",
        scan_id="scan:second",
    )
    return StoreFixture(
        store=store,
        older_project_id=older_id,
        newer_project_id=newer_id,
        older_map_json=older_map,
        newer_map_json=newer_map,
    )


def test_build_result_returns_none_when_artifacts_are_invalid(
    tmp_path: Path,
) -> None:
    """A tampered canonical map must read as missing, not raise."""
    fixture = _store_with_two_builds(tmp_path)
    fixture.newer_map_json.write_text("{}", encoding="utf-8")

    assert fixture.store.build_result(fixture.newer_project_id) is None


def test_build_results_skips_projects_with_invalid_artifacts(
    tmp_path: Path,
) -> None:
    """One broken project must not take the whole batch down."""
    fixture = _store_with_two_builds(tmp_path)
    fixture.older_map_json.write_text("{}", encoding="utf-8")

    results = fixture.store.build_results()

    assert [project_id for project_id, _ in results] == [
        fixture.newer_project_id
    ]
