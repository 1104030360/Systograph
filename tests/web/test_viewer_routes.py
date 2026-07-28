from __future__ import annotations

import inspect
from pathlib import Path

from fastapi.testclient import TestClient

import systograph.web.routes.viewer_routes as viewer_routes
from systograph.web.app import create_app

FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
INVALID_FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/invalid_confidence.v1.json"
)


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
