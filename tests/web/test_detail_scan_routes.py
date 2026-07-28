from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.web.test_detail_scan_build_binding import prepare_detail_scan

from kai_mind.web.app import create_app


def test_detail_scan_result_is_readable_by_id(tmp_path: Path) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
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
            "scan_depth": "code_path",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["detail_scan"]["target"] == target_id
    assert payload["detail_scan"]["scan_depth"] == "code_path"
    assert payload["detail_scan"]["best_effort"] is True
    assert "detail_scans" not in payload["ai_system_map"]

    detail_scan_id = payload["detail_scan"]["id"]
    get_response = client.get(f"/api/detail-scans/{detail_scan_id}")

    assert get_response.status_code == 200
    assert get_response.json()["detail_scan"]["id"] == detail_scan_id
    assert get_response.json()["project_id"] == project_id


def test_detail_scan_lookup_survives_a_corrupt_neighbour_project(
    tmp_path: Path,
) -> None:
    """鄰居 project 的 state 壞掉，不可以害健康 project 的查詢 500。

    這支 route 走 `store.build_results()` 掃全部 project 找那一筆
    detail scan，所以任何一個 project 的壞 `latest.json` 都會讓**所有**
    project 的 detail scan 查詢一起掛掉。
    """
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    healthy_root = tmp_path / "healthy"
    neighbour_root = tmp_path / "neighbour"
    healthy_root.mkdir()
    neighbour_root.mkdir()
    project_id, _, base_build_id, target_id, _ = prepare_detail_scan(
        client,
        healthy_root,
    )
    neighbour_id, _, _, _, _ = prepare_detail_scan(client, neighbour_root)
    created = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": target_id,
            "scan_depth": "code_path",
        },
    )
    assert created.status_code == 200
    detail_scan_id = created.json()["detail_scan"]["id"]

    neighbour_dir = state_dir / "projects" / neighbour_id.replace(":", "_")
    (neighbour_dir / "latest.json").write_text("{not json", encoding="utf-8")

    response = client.get(f"/api/detail-scans/{detail_scan_id}")

    assert response.status_code == 200
    assert response.json()["project_id"] == project_id


def test_detail_scan_route_rejects_invalid_target_without_writing(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, base_build_id, _, _ = prepare_detail_scan(
        client,
        tmp_path,
    )

    response = client.post(
        "/api/detail-scans",
        json={
            "project_id": project_id,
            "build_id": base_build_id,
            "target_type": "unmapped_component",
            "target": "unmapped:missing",
            "scan_depth": "component",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "target_not_found"
    latest = client.get(f"/api/projects/{project_id}/map-builds/latest").json()
    assert latest["build_id"] == base_build_id
    assert client.get(f"/api/detail-scans/{base_build_id}").status_code == 404
