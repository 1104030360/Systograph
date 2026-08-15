from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.scan import OutputRun, ProjectScanResult
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from systograph.core.services.build_commit_service import (
    BuildCommitError,
    BuildCommitService,
)
from systograph.core.services.build_manifest_artifacts import (
    required_artifact_paths,
    validate_artifact_references,
)
from systograph.core.services.build_manifest_service import (
    BuildManifestService,
)
from systograph.core.services.map_build_query_service import (
    MapBuildQueryService,
)
from systograph.core.services.map_build_service import MapBuildService


class FailingNthWriteProvider(OutputArtifactProvider):
    def __init__(self, fail_at: int) -> None:
        super().__init__()
        self._fail_at = fail_at
        self._writes = 0

    def _write_text_atomic(self, path: Path, content: str) -> Path:
        self._writes += 1
        if self._writes == self._fail_at:
            raise OSError("injected artifact write failure")
        return super()._write_text_atomic(path, content)


def snapshot() -> ScanSnapshot:
    return ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=datetime(2026, 7, 17, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(),
    )


def build_operation(
    tmp_path: Path,
    build_id: str,
    *,
    provider: OutputArtifactProvider | None = None,
) -> Callable[[OutputRun], MapBuildResult]:
    project_root = tmp_path / "project"
    project_root.mkdir(exist_ok=True)
    service = MapBuildService(output_artifact_provider=provider)

    def build(output_run: OutputRun) -> MapBuildResult:
        return service.build_from_snapshot(
            snapshot(),
            request=MapBuildRequest(
                project_path=project_root,
                output=output_run.root_dir.parent,
            ),
            output_run=output_run,
            build_id=build_id,
            build_reason="initial_scan",
        )

    return build


def commit_service(
    tmp_path: Path,
) -> tuple[
    BuildCommitService,
    LocalJsonStateProvider,
    MapBuildQueryService,
]:
    state = LocalJsonStateProvider(tmp_path / "state")
    manifests = BuildManifestService(repository=state)
    return (
        BuildCommitService(repository=state, manifest_service=manifests),
        state,
        MapBuildQueryService(
            repository=state,
            manifest_service=manifests,
        ),
    )


def test_commit_publishes_complete_set_before_manifest_and_latest(
    tmp_path: Path,
) -> None:
    service, state, query = commit_service(tmp_path)
    final_dir = tmp_path / "outputs" / "build_b1"

    result = service.commit(
        project_id="project:demo",
        build_id="build:b1",
        final_output_dir=final_dir,
        expected_latest_build_id=None,
        expected_revision=0,
        build=build_operation(tmp_path, "build:b1"),
    )

    manifest = state.get_build_manifest("project:demo", "build:b1")
    assert result.output_run_dir == final_dir
    assert final_dir.is_dir()
    assert not final_dir.with_name("build_b1.staging").exists()
    assert manifest is not None
    assert manifest.status == "complete"
    assert len(manifest.artifact_digests) == 10
    assert set(manifest.artifacts) == set(manifest.artifact_digests)
    assert all(
        entry.schema_status == "validated"
        and entry.size_bytes > 0
        and entry.digest == manifest.artifact_digests[name]
        for name, entry in manifest.artifacts.items()
    )
    assert all(
        manifest.artifacts[name].schema_version is not None
        for name in manifest.artifacts
        if name.endswith(".json")
    )
    for name in (
        "ai_system_map.md",
        "system_map.mmd",
        "execution_map.mmd",
    ):
        rendered = (final_dir / name).read_text(encoding="utf-8")
        assert "build:b1" in rendered
        assert "scan:s1" in rendered
        assert "environment:default-static" in rendered
        assert "phase2-p0/v1" in rendered
    assert query.latest("project:demo").lineage == result.lineage


@pytest.mark.parametrize("fail_at", range(1, 11))
def test_each_artifact_write_failure_remains_invisible(
    tmp_path: Path,
    fail_at: int,
) -> None:
    service, state, _ = commit_service(tmp_path)
    final_dir = tmp_path / "outputs" / "build_b1"

    with pytest.raises(OSError, match="injected artifact write failure"):
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build_operation(
                tmp_path,
                "build:b1",
                provider=FailingNthWriteProvider(fail_at),
            ),
        )

    assert not final_dir.exists()
    assert not final_dir.with_name("build_b1.staging").exists()
    assert state.get_build_manifest("project:demo", "build:b1") is None
    assert state.get_latest_pointer("project:demo") is None


def test_existing_final_directory_fails_without_running_builder(
    tmp_path: Path,
) -> None:
    service, _, _ = commit_service(tmp_path)
    final_dir = tmp_path / "outputs" / "build_b1"
    final_dir.mkdir(parents=True)
    called = False

    def build(output_run: OutputRun) -> MapBuildResult:
        nonlocal called
        called = True
        raise AssertionError(output_run)

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build,
        )

    assert captured.value.code == "build_output_conflict"
    assert called is False


def test_stale_pointer_keeps_complete_build_as_non_latest_history(
    tmp_path: Path,
) -> None:
    service, state, query = commit_service(tmp_path)
    output_root = tmp_path / "outputs"
    first = service.commit(
        project_id="project:demo",
        build_id="build:b1",
        final_output_dir=output_root / "build_b1",
        expected_latest_build_id=None,
        expected_revision=0,
        build=build_operation(tmp_path, "build:b1"),
    )

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b2",
            final_output_dir=output_root / "build_b2",
            expected_latest_build_id=None,
            expected_revision=0,
            build=build_operation(tmp_path, "build:b2"),
        )

    assert captured.value.code == "stale_latest_revision"
    assert state.get_build_manifest("project:demo", "build:b2") is not None
    assert (output_root / "build_b2").is_dir()
    assert query.latest("project:demo").lineage == first.lineage
    assert query.get("build:b2").lineage is not None


def test_supported_reader_cannot_find_staging_build(
    tmp_path: Path,
) -> None:
    service, _, query = commit_service(tmp_path)
    operation = build_operation(tmp_path, "build:b1")

    def build(output_run: OutputRun) -> MapBuildResult:
        result = operation(output_run)
        with pytest.raises(KeyError):
            query.get("build:b1")
        return result

    service.commit(
        project_id="project:demo",
        build_id="build:b1",
        final_output_dir=tmp_path / "outputs" / "build_b1",
        expected_latest_build_id=None,
        expected_revision=0,
        build=build,
    )

    assert query.get("build:b1").status == "ok"


@pytest.mark.parametrize(
    ("artifact_name", "field", "value"),
    [
        ("profile_signals.json", "environment_id", "environment:wrong"),
        ("readiness_report.json", "artifact_set_version", "wrong/v1"),
    ],
)
def test_scope_mismatch_never_publishes_artifact_set(
    tmp_path: Path,
    artifact_name: str,
    field: str,
    value: str,
) -> None:
    service, state, _ = commit_service(tmp_path)
    operation = build_operation(tmp_path, "build:b1")
    final_dir = tmp_path / "outputs" / "build_b1"

    def build(output_run: OutputRun) -> MapBuildResult:
        result = operation(output_run)
        path = output_run.root_dir / artifact_name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload[field] = value
        path.write_text(json.dumps(payload), encoding="utf-8")
        return result

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build,
        )

    assert captured.value.code == "build_artifact_set_invalid"
    assert not final_dir.exists()
    assert state.get_build_manifest("project:demo", "build:b1") is None


def test_dangling_evidence_reference_never_publishes_artifact_set(
    tmp_path: Path,
) -> None:
    service, state, _ = commit_service(tmp_path)
    operation = build_operation(tmp_path, "build:b1")
    final_dir = tmp_path / "outputs" / "build_b1"

    def build(output_run: OutputRun) -> MapBuildResult:
        result = operation(output_run)
        path = output_run.root_dir / "evidence_table.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"].append(
            {
                "evidence_id": "evidence:missing",
                "artifact_type": "source_file",
                "evidence_kind": "direct",
            }
        )
        path.write_text(json.dumps(payload), encoding="utf-8")
        return result

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build,
        )

    assert captured.value.code == "build_artifact_set_invalid"
    assert not final_dir.exists()
    assert state.get_build_manifest("project:demo", "build:b1") is None


def test_execution_path_dangling_reference_never_publishes_artifact_set(
    tmp_path: Path,
) -> None:
    # Given a valid build whose v2 execution path is tampered after generation.
    service, state, _ = commit_service(tmp_path)
    operation = build_operation(tmp_path, "build:b1")
    final_dir = tmp_path / "outputs" / "build_b1"

    def build(output_run: OutputRun) -> MapBuildResult:
        result = operation(output_run)
        path = output_run.root_dir / "execution_paths.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["paths"].append(
            {
                "edge_id": "edge:dangling",
                "source": "component:missing",
                "target": "component:missing",
                "relationship": "calls",
                "status": "observed",
                "evidence_ids": [],
            }
        )
        path.write_text(json.dumps(payload), encoding="utf-8")
        return result

    # When the artifact set is committed, then dangling endpoints fail closed.
    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build,
        )

    assert captured.value.code == "build_artifact_set_invalid"
    assert not final_dir.exists()
    assert state.get_build_manifest("project:demo", "build:b1") is None


def test_execution_path_unknown_evidence_fails_reference_validation(
    tmp_path: Path,
) -> None:
    operation = build_operation(tmp_path, "build:b1")
    result = operation(OutputRun(root_dir=tmp_path / "staging"))
    path = result.execution_paths_path
    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["paths"].append(
        {
            "edge_id": "edge:unknown-evidence",
            "source": "component:missing",
            "target": "component:missing",
            "relationship": "calls",
            "status": "observed",
            "evidence_ids": ["evidence:missing"],
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="artifact evidence reference mismatch: execution_paths.json",
    ):
        validate_artifact_references(
            result,
            required_artifact_paths(result),
        )


def test_invalid_sibling_schema_never_publishes_artifact_set(
    tmp_path: Path,
) -> None:
    service, state, _ = commit_service(tmp_path)
    operation = build_operation(tmp_path, "build:b1")
    final_dir = tmp_path / "outputs" / "build_b1"

    def build(output_run: OutputRun) -> MapBuildResult:
        result = operation(output_run)
        path = output_run.root_dir / "readiness_report.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["findings"] = "invalid"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return result

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build,
        )

    assert captured.value.code == "build_artifact_set_invalid"
    assert not final_dir.exists()
    assert state.get_build_manifest("project:demo", "build:b1") is None


def test_directory_rename_failure_never_persists_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, state, _ = commit_service(tmp_path)
    final_dir = tmp_path / "outputs" / "build_b1"

    def fail_rename(source: Path, target: Path) -> None:
        raise OSError(f"rename unavailable: {source.name} {target.name}")

    monkeypatch.setattr(
        "systograph.core.services.build_commit_service.os.rename",
        fail_rename,
    )

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build_operation(tmp_path, "build:b1"),
        )

    assert captured.value.code == "atomic_artifact_publish_unavailable"
    assert not final_dir.exists()
    assert not final_dir.with_name("build_b1.staging").exists()
    assert state.get_build_manifest("project:demo", "build:b1") is None


def test_manifest_failure_leaves_recoverable_orphan_final_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, state, _ = commit_service(tmp_path)
    final_dir = tmp_path / "outputs" / "build_b1"

    def fail_persist(
        result: MapBuildResult,
        *,
        apply_request_digest: str | None = None,
    ) -> None:
        del result, apply_request_digest
        raise ValueError("injected manifest failure")

    monkeypatch.setattr(service._manifest, "persist", fail_persist)

    with pytest.raises(BuildCommitError) as captured:
        service.commit(
            project_id="project:demo",
            build_id="build:b1",
            final_output_dir=final_dir,
            expected_latest_build_id=None,
            expected_revision=0,
            build=build_operation(tmp_path, "build:b1"),
        )

    assert captured.value.code == "build_manifest_persist_failed"
    assert final_dir.is_dir()
    assert state.get_build_manifest("project:demo", "build:b1") is None
    assert state.get_latest_pointer("project:demo") is None

    service.discard_orphan_artifact_set(
        project_id="project:demo",
        build_id="build:b1",
        final_output_dir=final_dir,
    )

    assert not final_dir.exists()
