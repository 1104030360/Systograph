"""Unit tests for the web session store implementations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import pytest

from kai_mind.core.models.analysis_history import ScanSnapshot
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
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
    manifest_service: BuildManifestService
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
        manifest_service=manifest_service,
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


def test_build_result_returns_none_when_artifact_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OSError 也算失效，不可以冒出來。

    `digest_matches` 先 `path.is_file()` 再 `read_bytes()`
    （`build_manifest_artifacts.py:235-245`），中間檔案可能不可讀或剛被刪，
    而那個 `read_bytes` 不在任何 try 裡面 —— 只接
    `BuildArtifactLoadError` 會讓這條路徑照樣 500。
    """
    fixture = _store_with_two_builds(tmp_path)

    def unreadable(*args: object, **kwargs: object) -> MapBuildResult:
        raise PermissionError(13, "Permission denied", "ai_system_map.json")

    monkeypatch.setattr(fixture.manifest_service, "load", unreadable)

    assert fixture.store.build_result(fixture.newer_project_id) is None
    assert fixture.store.build_results() == ()


def test_build_result_lookup_does_not_change_latest_build_result(
    tmp_path: Path,
) -> None:
    """查舊 project 不可以讓 latest_build_result 變成舊的那個。"""
    fixture = _store_with_two_builds(tmp_path)

    newest_before = fixture.store.latest_build_result()
    assert newest_before is not None
    assert newest_before.lineage is not None
    assert newest_before.lineage.build_id == "build:second"

    fixture.store.build_result(fixture.older_project_id)

    newest_after = fixture.store.latest_build_result()
    assert newest_after is not None
    assert newest_after.lineage is not None
    assert newest_after.lineage.build_id == "build:second"
    assert newest_after == newest_before


def test_concurrent_save_and_read_keeps_state_consistent(
    tmp_path: Path,
) -> None:
    """並行讀寫不可以炸出例外。

    這是回歸護欄，不是 RED-first 證明：兩個欄位被切開更新的中間狀態
    無法從公開 API 穩定觀察到，所以這裡只確認鎖沒有造成死鎖／例外，
    且收斂後的狀態仍然可用。
    """
    fixture = _store_with_two_builds(tmp_path)
    store = fixture.store
    newer = fixture.newer_project_id
    errors: list[BaseException] = []

    def reader() -> None:
        try:
            for _ in range(200):
                store.latest_build_result()
                store.latest_viewer_payload()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def writer() -> None:
        try:
            for _ in range(200):
                result = store.build_result(newer)
                if result is not None:
                    store.save_build_result(result, project_id=newer)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(reader),
            pool.submit(reader),
            pool.submit(writer),
            pool.submit(writer),
        ]
        for future in futures:
            future.result()

    assert not errors
    settled = store.latest_build_result()
    assert settled is not None
    assert settled.lineage is not None
    assert settled.lineage.build_id == "build:second"
