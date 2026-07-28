from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from filelock import FileLock

from systograph.core.models.analysis_history import (
    MapBuildLineage,
    MapBuildManifest,
    ProjectState,
)
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
    ProjectStateBusyError,
    StateConflictError,
)


def project(project_id: str) -> ProjectState:
    return ProjectState(
        project_id=project_id,
        project_name=project_id.removeprefix("project:"),
        source_type="local_path",
        canonical_path=f"/tmp/{project_id.replace(':', '_')}",
        path_digest=f"sha256:{project_id}",
        created_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
    )


def manifest(
    build_id: str,
    *,
    parent: str | None = None,
    mapping_id: str | None = None,
) -> MapBuildManifest:
    return MapBuildManifest(
        lineage=MapBuildLineage(
            project_id="project:demo",
            scan_id="scan:s1",
            build_id=build_id,
            based_on_build_id=parent,
            build_reason=("apply_confirmations" if parent else "initial_scan"),
            applied_mapping_ids=((mapping_id,) if mapping_id else ()),
            generated_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        ),
        output_dir=f"/tmp/output/{build_id.replace(':', '_')}",
        artifact_digests={"ai_system_map.json": f"sha256:{build_id}"},
    )


def test_concurrent_same_base_promotions_have_one_winner(
    tmp_path: Path,
) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project("project:demo"))
    provider.save_build_manifest(manifest("build:b1"))
    provider.save_build_manifest(
        manifest("build:b2", parent="build:b1", mapping_id="mapping:m1")
    )
    provider.save_build_manifest(
        manifest("build:b3", parent="build:b1", mapping_id="mapping:m2")
    )
    provider.promote_latest_build(
        project_id="project:demo",
        build_id="build:b1",
        expected_latest_build_id=None,
        expected_revision=0,
    )

    def promote(build_id: str) -> str:
        try:
            provider.promote_latest_build(
                project_id="project:demo",
                build_id=build_id,
                expected_latest_build_id="build:b1",
                expected_revision=1,
            )
        except StateConflictError:
            return "stale"
        return "promoted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(promote, ("build:b2", "build:b3")))

    assert sorted(outcomes) == ["promoted", "stale"]
    latest = provider.get_latest_pointer("project:demo")
    assert latest is not None
    assert latest.revision == 2


def test_project_locks_do_not_block_another_project(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path, lock_timeout=0.05)
    provider.save_project(project("project:a"))
    lock_path = tmp_path / "projects" / "project_a" / ".project.lock"

    with FileLock(str(lock_path)):
        saved = provider.save_project(project("project:b"))

    assert saved.project_id == "project:b"


def test_same_project_lock_timeout_fails_closed(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path, lock_timeout=0.01)
    lock_path = tmp_path / "projects" / "project_demo" / ".project.lock"
    lock_path.parent.mkdir(parents=True)

    with FileLock(str(lock_path)):
        with pytest.raises(ProjectStateBusyError, match="project_state_busy"):
            provider.save_project(project("project:demo"))
