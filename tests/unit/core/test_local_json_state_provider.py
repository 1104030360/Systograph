from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kai_mind.core.models.analysis_history import (
    MapBuildLineage,
    MapBuildManifest,
    ProjectState,
    ScanSnapshot,
)
from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingDecision,
    ManualMappingType,
)
from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.providers.local_json_state_provider import (
    InvalidStateIdError,
    LocalJsonStateProvider,
    StateConflictError,
    StateCorruptionError,
)


def now() -> datetime:
    return datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


def confirmed_mapping() -> ManualMapping:
    return ManualMapping(
        project_id="project:demo",
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id="unmapped:retriever",
        source_file="src/retriever.py",
        observed_kind="retriever",
        evidence_ids=["evidence:retriever"],
        target_slot="retriever",
        component_name="Demo Retriever",
        mapping_id="mapping:m1",
        mapping_digest="sha256:m1",
        created_at="2026-07-11T12:00:00Z",
        updated_at="2026-07-11T12:00:00Z",
    )


def project_state() -> ProjectState:
    return ProjectState(
        project_id="project:demo",
        project_name="demo",
        source_type="local_path",
        canonical_path="/tmp/projects/demo",
        path_digest="sha256:path",
        created_at=now(),
    )


def snapshot() -> ScanSnapshot:
    return ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=now(),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(files_scanned=1),
    )


def build_manifest(build_id: str = "build:b1") -> MapBuildManifest:
    return MapBuildManifest(
        lineage=MapBuildLineage(
            project_id="project:demo",
            scan_id="scan:s1",
            build_id=build_id,
            build_reason="initial_scan",
            generated_at=now(),
        ),
        output_dir=f"/tmp/output/{build_id.replace(':', '_')}",
        artifact_digests={"ai_system_map.json": "sha256:map"},
    )


def test_state_survives_provider_recreation(tmp_path: Path) -> None:
    first = LocalJsonStateProvider(tmp_path)
    first.save_project(project_state())
    first.save(confirmed_mapping())
    first.save_snapshot(snapshot())

    second = LocalJsonStateProvider(tmp_path)

    assert second.get("mapping:m1") == confirmed_mapping()
    assert second.get_snapshot("project:demo", "scan:s1") == snapshot()
    assert second.find_project_by_path_digest("sha256:path") == project_state()


def test_latest_build_promotion_uses_revision_cas(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project_state())
    provider.save_build_manifest(build_manifest())

    first = provider.promote_latest_build(
        project_id="project:demo",
        build_id="build:b1",
        expected_latest_build_id=None,
        expected_revision=0,
    )

    assert first.revision == 1
    assert provider.get_latest_build_id("project:demo") == "build:b1"
    with pytest.raises(StateConflictError, match="stale latest revision"):
        provider.promote_latest_build(
            project_id="project:demo",
            build_id="build:b1",
            expected_latest_build_id=None,
            expected_revision=0,
        )


@pytest.mark.parametrize(
    "project_id",
    ["project:../escape", "project:..", "project:alpha..beta"],
)
def test_provider_rejects_path_traversal_ids(
    tmp_path: Path,
    project_id: str,
) -> None:
    provider = LocalJsonStateProvider(tmp_path)

    with pytest.raises(InvalidStateIdError):
        provider.get_snapshot(project_id, "scan:s1")


def test_provider_fails_closed_on_corrupt_json(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project_state())
    project_file = tmp_path / "projects" / "project_demo" / "project.json"
    project_file.write_text("{broken", encoding="utf-8")

    with pytest.raises(StateCorruptionError):
        provider.get_project("project:demo")


def test_snapshot_is_masked_before_persistence(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    unsafe = snapshot().model_copy(
        update={
            "scan_result": ProjectScanResult(
                warnings=["OPENAI_API_KEY=sk-live-example-value"]
            )
        }
    )

    provider.save_snapshot(unsafe)

    snapshot_path = (
        tmp_path
        / "projects"
        / "project_demo"
        / "scans"
        / "scan_s1"
        / "snapshot.json"
    )
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert "sk-live-example-value" not in json.dumps(payload)
    assert "..." in json.dumps(payload)


def test_serialization_is_deterministic_and_keeps_temp_files_separate(
    tmp_path: Path,
) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project_state())
    path = tmp_path / "projects" / "project_demo" / "project.json"
    first = path.read_bytes()

    provider.save_project(project_state())

    assert path.read_bytes() == first
    assert not list(path.parent.glob("*.tmp"))


def test_duplicate_immutable_ids_reject_changed_state(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project_state())
    provider.save_snapshot(snapshot())
    provider.save_build_manifest(build_manifest())

    with pytest.raises(StateConflictError, match="scan snapshot is immutable"):
        provider.save_snapshot(
            snapshot().model_copy(
                update={"inventory_digest": "sha256:changed"}
            )
        )
    with pytest.raises(
        StateConflictError,
        match="build manifest is immutable",
    ):
        provider.save_build_manifest(
            build_manifest().model_copy(update={"output_dir": "/tmp/changed"})
        )


def test_project_scoped_lookup_does_not_cross_project_boundary(
    tmp_path: Path,
) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project_state())
    provider.save_project(
        project_state().model_copy(
            update={
                "project_id": "project:other",
                "project_name": "other",
                "canonical_path": "/tmp/projects/other",
                "path_digest": "sha256:other",
            }
        )
    )
    provider.save_snapshot(snapshot())
    provider.save_build_manifest(build_manifest())

    assert provider.get_snapshot("project:other", "scan:s1") is None
    assert provider.get_build_manifest("project:other", "build:b1") is None


def test_interrupted_temp_file_is_ignored(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_project(project_state())
    project_dir = tmp_path / "projects" / "project_demo"
    (project_dir / ".project.json.interrupted.tmp").write_text(
        "{broken",
        encoding="utf-8",
    )

    assert provider.get_project("project:demo") == project_state()
