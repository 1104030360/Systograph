from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from tests.web.test_detail_scan_build_binding import prepare_detail_scan
from tests.web.test_map_build_apply_routes import apply, prepare_apply

from kai_mind.web.app import create_app


def _mark_manifest_as_pre_cutover(
    state_dir: Path,
    project_id: str,
    build_id: str,
) -> None:
    manifest_path = (
        state_dir
        / "projects"
        / project_id.replace(":", "_")
        / "builds"
        / build_id.replace(":", "_")
        / "manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["requested_schema_version"] = "ai-system-map/v1"
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def test_v2_active_metadata_survives_restart(tmp_path: Path) -> None:
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
    assert payload["active_schema_version"] == "ai-system-map/v2"
    assert payload["requested_schema_version"] == "ai-system-map/v2"
    assert payload["source_schema_version"] == "ai-system-map/v2"
    assert payload["operator_rollback_active"] is False
    assert payload["migration_warnings"] == original["migration_warnings"]


def test_apply_rebuilds_pre_cutover_manifest_as_v2(tmp_path: Path) -> None:
    # Given a persisted build whose request predates the v2-only cutover.
    state_dir = tmp_path / "state"
    first = TestClient(create_app(state_dir=state_dir))
    project_id, base_build_id, mapping_id = prepare_apply(first, tmp_path)
    _mark_manifest_as_pre_cutover(state_dir, project_id, base_build_id)
    restarted = TestClient(create_app(state_dir=state_dir))

    # When confirmations are applied from the historical build.
    response = apply(restarted, base_build_id, mapping_id)

    # Then the child build uses the current canonical schema selection.
    assert response.status_code == 200
    child = response.json()["build_result"]
    assert child["requested_schema_version"] == "ai-system-map/v2"
    assert child["active_schema_version"] == "ai-system-map/v2"


def test_detail_scan_rebuilds_pre_cutover_manifest_as_v2(
    tmp_path: Path,
) -> None:
    # Given a persisted build whose request predates the v2-only cutover.
    state_dir = tmp_path / "state"
    first = TestClient(create_app(state_dir=state_dir))
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
        first,
        tmp_path,
    )
    _mark_manifest_as_pre_cutover(state_dir, project_id, base_build_id)
    restarted = TestClient(create_app(state_dir=state_dir))

    # When a detail scan creates a child build from that historical build.
    response = restarted.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    # Then the child build uses the current canonical schema selection.
    assert response.status_code == 200
    child = restarted.get(
        f"/api/map-builds/{response.json()['build_id']}"
    ).json()["build_result"]
    assert child["requested_schema_version"] == "ai-system-map/v2"
    assert child["active_schema_version"] == "ai-system-map/v2"


def test_committed_detail_scan_survives_restart(tmp_path: Path) -> None:
    # Given a detail scan committed as the latest child build.
    state_dir = tmp_path / "state"
    first = TestClient(create_app(state_dir=state_dir))
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
        first,
        tmp_path,
    )
    committed = first.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )
    assert committed.status_code == 200
    detail_scan_id = committed.json()["detail_scan"]["id"]

    # When a fresh app process reads the committed build from its manifest.
    restarted = TestClient(create_app(state_dir=state_dir))
    recovered = restarted.get(f"/api/detail-scans/{detail_scan_id}")

    # Then the committed detail scan remains addressable.
    assert recovered.status_code == 200
    assert recovered.json()["detail_scan"]["id"] == detail_scan_id


def test_latest_viewer_payload_survives_restart(tmp_path: Path) -> None:
    """新 app 物件 + 舊 state_dir 時，/api/map 仍要還原最新 build。

    這條驗的是 `create_app()` 開機時那一次
    `PersistentSessionStore.hydrate_from_latest()` —— 同一個 process 內
    永遠走不到，只有 restart 情境會觸發。`/api/map` 本身只讀快取，
    所以 hydrate 沒被呼叫到的話這條一定紅。
    """
    state_dir = tmp_path / "state"
    first = TestClient(create_app(state_dir=state_dir))
    prepare_apply(first, tmp_path)
    before = first.get("/api/map").json()
    assert before["viewer_load_result"]["loaded"] is True

    second = TestClient(create_app(state_dir=state_dir))
    after = second.get("/api/map").json()

    assert after["viewer_load_result"]["loaded"] is True
    assert after == before
    assert second.get("/api/map/report").status_code == 200
