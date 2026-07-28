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
from kai_mind.core.models.viewer import ViewerPayload
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
    StateCorruptionError,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.session_store import (
    InMemorySessionStore,
    PersistentSessionStore,
)


class StoreFixture(NamedTuple):
    """One session store plus two published builds on disk."""

    store: PersistentSessionStore
    repository: LocalJsonStateProvider
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


def _project_dir(tmp_path: Path, project_id: str) -> Path:
    return tmp_path / "state" / "projects" / project_id.replace(":", "_")


def _latest_pointer_path(tmp_path: Path, project_id: str) -> Path:
    return _project_dir(tmp_path, project_id) / "latest.json"


def _manifest_path(tmp_path: Path, project_id: str, build_id: str) -> Path:
    return (
        _project_dir(tmp_path, project_id)
        / "builds"
        / build_id.replace(":", "_")
        / "manifest.json"
    )


def _corrupt(path: Path) -> None:
    """真的把 state JSON 寫壞（不是 monkeypatch）。"""
    assert path.is_file(), path
    path.write_text("{not json", encoding="utf-8")


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
        repository=repository,
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


def test_hydrate_seeds_the_viewer_payload_from_the_newest_build(
    tmp_path: Path,
) -> None:
    """開機預熱：沒 hydrate 前是空的，hydrate 後是磁碟上最新那一份。"""
    fixture = _store_with_two_builds(tmp_path)

    before = fixture.store.latest_viewer_payload()
    assert before.viewer_load_result.loaded is False

    fixture.store.hydrate_from_latest()

    hydrated = fixture.store.latest_viewer_payload().viewer_load_result
    assert hydrated.loaded is True
    assert hydrated.ai_system_map["build_id"] == "build:second"


def test_hydrate_falls_back_to_the_next_newest_loadable_build(
    tmp_path: Path,
) -> None:
    """最新的 project 壞掉時，往下找 —— 不可以讓 viewer 整個空白。

    這是刻意跟 `latest_build_result()` 分道揚鑣的地方：那支只看最新
    那一個（呼叫端要的就是「最新」），hydrate 是開機預熱，一個壞掉的
    project 不該連累其他 project 已經有的好 build。
    """
    fixture = _store_with_two_builds(tmp_path)
    fixture.newer_map_json.write_text("{}", encoding="utf-8")

    fixture.store.hydrate_from_latest()

    hydrated = fixture.store.latest_viewer_payload().viewer_load_result
    assert hydrated.loaded is True
    assert hydrated.ai_system_map["build_id"] == "build:first"
    # 對照組：latest_build_result() 維持原語意，最新的壞掉就是 None。
    assert fixture.store.latest_build_result() is None


def test_hydrate_keeps_the_empty_payload_when_every_build_is_invalid(
    tmp_path: Path,
) -> None:
    """全部壞掉時安靜留在空 payload，不丟例外。"""
    fixture = _store_with_two_builds(tmp_path)
    fixture.newer_map_json.write_text("{}", encoding="utf-8")
    fixture.older_map_json.write_text("{}", encoding="utf-8")

    fixture.store.hydrate_from_latest()

    payload = fixture.store.latest_viewer_payload().viewer_load_result
    assert payload.loaded is False
    assert payload.error_reason == "no_map_loaded"


def test_hydrate_skips_a_project_whose_latest_pointer_is_corrupt(
    tmp_path: Path,
) -> None:
    """壞掉的 `latest.json` 只能拖垮它自己那個 project。

    `get_latest_pointer()` 讀到壞 JSON 會丟 `StateCorruptionError`，
    而且是在「由新到舊」的迴圈**開始之前**（列 pointer 的時候）——
    容錯若只包在迴圈裡，最新那個 project 的壞 pointer 照樣清空 viewer。
    """
    fixture = _store_with_two_builds(tmp_path)
    _corrupt(_latest_pointer_path(tmp_path, fixture.newer_project_id))

    fixture.store.hydrate_from_latest()

    hydrated = fixture.store.latest_viewer_payload().viewer_load_result
    assert hydrated.loaded is True
    assert hydrated.ai_system_map["build_id"] == "build:first"
    # 但 latest_build_result() 必須 fail closed：pointer 讀不出來時，
    # 「誰是最新」就是不可知的（讀不出來的那個可能才是最新），
    # 絕不可以拿別人的 build 冒充 → 走既有的 404。
    assert fixture.store.latest_build_result() is None


def test_hydrate_skips_a_project_whose_manifest_is_corrupt(
    tmp_path: Path,
) -> None:
    """壞掉的 `manifest.json` 同理，只是它是從迴圈**裡面**丟出來的。

    `build_result()` 只接 `manifest_service.load()` 的
    `BuildArtifactLoadError`/`OSError`；`get_build_manifest()` 自己丟的
    `StateCorruptionError` 會直接穿過去。
    """
    fixture = _store_with_two_builds(tmp_path)
    _corrupt(
        _manifest_path(tmp_path, fixture.newer_project_id, "build:second")
    )

    fixture.store.hydrate_from_latest()

    hydrated = fixture.store.latest_viewer_payload().viewer_load_result
    assert hydrated.loaded is True
    assert hydrated.ai_system_map["build_id"] == "build:first"
    # latest_build_result() 這邊是「最新那一個載不起來」→ None（不是 500，
    # 也不是回次新的那一份）。跟 artifact digest 失效同一個結局。
    assert fixture.store.latest_build_result() is None


def test_hydrate_survives_a_corrupt_state_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """state dir 損壞不可以讓 create_app() 開不起來。

    `list_projects()` 讀到壞掉的 project.json 會丟 `StateCorruptionError`
    （`local_json_state_storage.py:88`）。hydrate 是預熱不是啟動前提，
    所以要吞掉並留在空 payload。
    """
    fixture = _store_with_two_builds(tmp_path)

    def corrupt() -> tuple[object, ...]:
        raise StateCorruptionError("invalid local state: project.json")

    monkeypatch.setattr(fixture.repository, "list_projects", corrupt)

    fixture.store.hydrate_from_latest()

    payload = fixture.store.latest_viewer_payload()
    assert payload.viewer_load_result.loaded is False


def test_latest_viewer_payload_is_a_plain_cache_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """viewer/load 寫進來的 payload 不可以被既有 build 蓋掉，也不可以再讀檔。

    讓 repository 一被碰就爆炸：`latest_viewer_payload()` 仍要回快取，
    證明它既沒有從 build 反推（`POST /api/viewer/load` 的契約），
    也沒有每個 request 重走一次磁碟（前端是輪詢這支的）。
    """
    fixture = _store_with_two_builds(tmp_path)
    fixture.store.hydrate_from_latest()
    loaded = ViewerPayload(
        viewer_load_result=ViewerSessionService().empty(
            error_reason="viewer_load_sentinel"
        )
    )
    fixture.store.save_viewer_payload(loaded)

    def explode() -> tuple[object, ...]:
        raise AssertionError("latest_viewer_payload must not touch the disk")

    monkeypatch.setattr(fixture.repository, "list_projects", explode)

    assert fixture.store.latest_viewer_payload() == loaded


def test_in_memory_hydrate_is_a_no_op() -> None:
    """記憶體實作沒有持久化來源，hydrate 不改任何東西。"""
    store = InMemorySessionStore()
    before = store.latest_viewer_payload()

    store.hydrate_from_latest()

    assert store.latest_viewer_payload() == before
    assert store.latest_build_result() is None


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
