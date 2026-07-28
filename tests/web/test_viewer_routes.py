from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import kai_mind.web.routes.viewer_routes as viewer_routes
from kai_mind.web.app import create_app

FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
INVALID_FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/invalid_confidence.v1.json"
)


def _build_a_map(client: TestClient, tmp_path: Path) -> dict[str, Any]:
    """Publish one real build so the store has a persisted latest build."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "chromadb==0.5.0\n",
        encoding="utf-8",
    )
    imported = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    )
    assert imported.status_code == 200
    scan = client.post(
        "/api/scans",
        json={
            "project_id": imported.json()["project_id"],
            "output": str(tmp_path / "output"),
        },
    )
    assert scan.status_code == 200
    built: dict[str, Any] = client.get("/api/map").json()
    return built


def _load_viewer_map(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/viewer/load",
        json={"map_json_path": str(FIXTURE_PATH)},
    )
    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert payload["viewer_load_result"]["loaded"] is True
    return payload


def test_viewer_load_route_updates_latest_payload() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/viewer/load",
        json={"map_json_path": str(FIXTURE_PATH)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["viewer_load_result"]["loaded"] is True
    graph = payload["viewer_load_result"]["graph_view_model"]
    assert graph["schema_version"] == "graph-view-model/v1"
    assert {
        node["source_id"] for node in graph["nodes"] if "source_id" in node
    } >= {
        "component:vector_store:qdrant",
        "extension:cache:redis-response-cache",
        "unmapped:src-rag-rerank",
    }

    latest_payload = client.get("/api/map").json()
    assert latest_payload == payload


def test_viewer_load_wins_over_an_existing_build(tmp_path: Path) -> None:
    """API-GUIDE `POST /api/viewer/load` —— load 之後它就是最新的 payload。

    只有「state dir 裡已經有 build」時才會走到這條分支：既有的
    `test_viewer_load_route_updates_latest_payload` 用空 state dir，
    永遠踩不到 build 蓋掉 viewer/load 的那一半。
    """
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    built = _build_a_map(client, tmp_path)
    assert built["viewer_load_result"]["loaded"] is True

    loaded = _load_viewer_map(client)

    assert loaded != built
    assert client.get("/api/map").json() == loaded


def test_viewer_load_route_returns_error_payload_for_invalid_map() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/viewer/load",
        json={"map_json_path": str(INVALID_FIXTURE_PATH)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["viewer_load_result"]["loaded"] is False
    assert "confidence" in payload["viewer_load_result"]["error_reason"]
    assert payload["viewer_load_result"]["graph_view_model"]["nodes"] == []


def test_viewer_route_is_thin_adapter_without_project_scan_logic() -> None:
    source = inspect.getsource(viewer_routes)

    assert "ViewerSessionService" in source
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
    assert "ConfigParseProvider" not in source
    assert "DockerComposeProvider" not in source
