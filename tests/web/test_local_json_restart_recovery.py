from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from tests.web.test_map_build_apply_routes import apply, prepare_apply

from kai_mind.web.app import create_app


def test_default_state_root_uses_environment_and_survives_restart(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    state_dir = tmp_path / "configured-state"
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setenv("KAI_MIND_STATE_DIR", str(state_dir))

    first = TestClient(create_app())
    original = first.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()

    second = TestClient(create_app())
    recovered = second.get(f"/api/projects/{original['project_id']}")

    assert recovered.status_code == 200
    assert (state_dir / "projects").is_dir()


def test_project_mapping_and_latest_build_survive_restart(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    first = TestClient(create_app(state_dir=state_dir))
    project_id, base_build_id, mapping_id = prepare_apply(first, tmp_path)
    applied = apply(first, base_build_id, mapping_id).json()

    second = TestClient(create_app(state_dir=state_dir))
    project = second.get(f"/api/projects/{project_id}")
    mappings = second.get(f"/api/mappings?project_id={project_id}")
    latest = second.get(f"/api/projects/{project_id}/map-builds/latest")

    assert (
        project.status_code
        == mappings.status_code
        == latest.status_code
        == 200
    )
    assert mappings.json()["mappings"][0]["mapping_id"] == mapping_id
    assert latest.json()["build_id"] == applied["build_id"]
    assert second.get(f"/api/map-builds/{base_build_id}").status_code == 200


def test_reimport_same_canonical_path_reuses_project_identity(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    project_root = tmp_path / "project"
    project_root.mkdir()
    first = TestClient(create_app(state_dir=state_dir))
    original = first.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()

    second = TestClient(create_app(state_dir=state_dir))
    imported = second.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root / "."),
        },
    ).json()

    assert imported["project_id"] == original["project_id"]
    assert imported["reused"] is True


def test_v2_opt_in_metadata_survives_restart(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    project_root = tmp_path / "project"
    project_root.mkdir()
    first = TestClient(create_app(state_dir=state_dir))
    project_id = first.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()["project_id"]
    original = first.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "output"),
            "system_map_schema_version": "ai-system-map/v2",
        },
    ).json()["build_result"]

    second = TestClient(create_app(state_dir=state_dir))
    recovered = second.get(
        f"/api/map-builds/{original['lineage']['build_id']}"
    )

    assert recovered.status_code == 200
    payload = recovered.json()["build_result"]
    assert payload["active_schema_version"] == "ai-system-map/v1"
    assert payload["requested_schema_version"] == "ai-system-map/v2"
    assert payload["migration_warnings"] == original["migration_warnings"]
