from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.web.test_map_build_apply_routes import prepare_apply

from kai_mind.web.app import create_app


def test_query_trace_binds_source_build_without_creating_child(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, build_id, _ = prepare_apply(client, tmp_path)
    before = client.get(f"/api/projects/{project_id}/map-builds").json()

    response = client.post(
        "/api/trace",
        json={
            "project_id": project_id,
            "build_id": build_id,
            "endpoint_id": "endpoint:missing",
            "query": "hello",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_build_id"] == build_id
    assert payload["source_scan_id"].startswith("scan:")
    after = client.get(f"/api/projects/{project_id}/map-builds").json()
    assert after == before


def test_query_trace_rejects_unknown_requested_build(tmp_path: Path) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, _, _ = prepare_apply(client, tmp_path)

    response = client.post(
        "/api/trace",
        json={
            "project_id": project_id,
            "build_id": "build:missing",
            "endpoint_id": "endpoint:missing",
            "query": "hello",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "build_not_found"
