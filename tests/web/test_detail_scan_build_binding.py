from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from kai_mind.core.models.map_build import SystemMapSchemaSelection
from kai_mind.web.app import create_app


def prepare_detail_scan(
    client: TestClient,
    tmp_path: Path,
    *,
    schema_version: SystemMapSchemaSelection = "ai-system-map/v1",
) -> tuple[str, str, str, str, Path]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "requirements.txt"
    target_file.write_text("chromadb==0.5.0\n", encoding="utf-8")
    project_id = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()["project_id"]
    scan = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "output"),
            "system_map_schema_version": schema_version,
        },
    ).json()
    build = scan["build_result"]
    return (
        project_id,
        scan["scan_id"],
        build["lineage"]["build_id"],
        build["ai_system_map"]["unmapped_components"][0]["id"],
        target_file,
    )


def test_detail_scan_creates_child_build_without_mutating_parent(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, scan_id, base_build_id, target_id, _ = prepare_detail_scan(
        client,
        tmp_path,
    )

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_build_id"] == base_build_id
    assert payload["build_id"] != base_build_id
    assert payload["scan_id"] == scan_id
    assert payload["viewer_load_result"]["loaded"] is True

    parent = client.get(f"/api/map-builds/{base_build_id}").json()
    child = client.get(f"/api/map-builds/{payload['build_id']}").json()
    latest = client.get(f"/api/projects/{project_id}/map-builds/latest").json()

    assert parent["build_reason"] == "initial_scan"
    assert child["build_reason"] == "detail_scan"
    assert child["based_on_build_id"] == base_build_id
    assert latest["build_id"] == payload["build_id"]


def test_detail_scan_rejects_file_changed_since_snapshot(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, base_build_id, target_id, target_file = prepare_detail_scan(
        client,
        tmp_path,
    )
    target_file.write_text("chromadb==0.6.0\n", encoding="utf-8")

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "scan_snapshot_stale"
    latest = client.get(f"/api/projects/{project_id}/map-builds/latest").json()
    assert latest["build_id"] == base_build_id


def test_detail_scan_preserves_parent_schema_selection(tmp_path: Path) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
        client,
        tmp_path,
        schema_version="ai-system-map/v2",
    )

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    assert response.status_code == 200
    child = client.get(f"/api/map-builds/{response.json()['build_id']}").json()
    assert child["build_result"]["requested_schema_version"] == (
        "ai-system-map/v2"
    )


def test_detail_scan_rejects_build_owned_by_another_project(
    tmp_path: Path,
) -> None:
    # Given
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    project_id, _, _, target_id, _ = prepare_detail_scan(
        client,
        first_root,
    )
    _, _, foreign_build_id, _, _ = prepare_detail_scan(
        client,
        second_root,
    )

    # When
    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": foreign_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    # Then
    assert response.status_code == 404
    assert response.json()["detail"] == "project_build_mismatch"


def test_detail_scan_rejects_base_build_after_latest_advances(
    tmp_path: Path,
) -> None:
    # Given
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
        client,
        tmp_path,
    )
    first_response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )
    assert first_response.status_code == 200

    # When
    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    # Then
    assert response.status_code == 409
    assert response.json()["detail"] == "base_build_not_latest"


def test_detail_scan_fails_closed_when_profile_sidecar_is_unavailable(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
        client,
        tmp_path,
    )
    profile_path = next(
        path
        for path in (tmp_path / "output").rglob("profile_signals.json")
        if json.loads(path.read_text(encoding="utf-8"))["build_id"]
        == base_build_id
    )
    profile_path.unlink()

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "component",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "profile_sidecar_unavailable"
    latest = client.get(f"/api/projects/{project_id}/map-builds/latest")
    assert latest.json()["build_id"] == base_build_id
