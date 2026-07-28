from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.unit.core.test_detail_scan_service import (
    base_map,
    build_router_project,
)

from systograph.core.models.map_build import MapBuildResult
from systograph.web.app import create_app
from systograph.web.session_store import InMemorySessionStore


def test_detail_scan_route_appends_result_to_project_map(
    tmp_path: Path,
) -> None:
    client, project_id, _store = create_detail_scan_test_client(tmp_path)

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "target_type": "unmapped_component",
            "target": "unmapped:router",
            "scan_depth": "code_path",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["detail_scan"]["target"] == "unmapped:router"
    assert payload["detail_scan"]["scan_depth"] == "code_path"
    assert payload["detail_scan"]["best_effort"] is True
    assert "detail_scans" not in payload["ai_system_map"]
    assert any(
        item["evidence_id"].startswith("evidence:detail-scan:")
        for item in payload["ai_system_map"]["evidence"]
    )

    detail_scan_id = payload["detail_scan"]["id"]
    get_response = client.get(f"/api/detail-scans/{detail_scan_id}")

    assert get_response.status_code == 200
    assert get_response.json()["detail_scan"]["id"] == detail_scan_id


def test_detail_scan_route_rejects_invalid_target_without_writing(
    tmp_path: Path,
) -> None:
    client, project_id, store = create_detail_scan_test_client(tmp_path)

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "target_type": "unmapped_component",
            "target": "unmapped:missing",
            "scan_depth": "component",
        },
    )
    build_result = store.build_result(project_id)

    assert response.status_code == 422
    assert response.json()["detail"] == "target_not_found"
    assert build_result is not None
    assert build_result.ai_system_map is not None
    assert build_result.detail_scan_results == []


def create_detail_scan_test_client(
    tmp_path: Path,
) -> tuple[TestClient, str, InMemorySessionStore]:
    project_root = build_router_project(tmp_path)
    store = InMemorySessionStore()
    project = store.import_project(
        project_path=project_root,
        source_type="local_path",
    )
    store.save_build_result(
        MapBuildResult(
            status="ok",
            project_name=project_root.name,
            ai_system_map=base_map(),
        ),
        project_id=project.project_id,
    )
    return (
        TestClient(create_app(session_store=store)),
        project.project_id,
        store,
    )
