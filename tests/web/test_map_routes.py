from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.web.app import create_app


def test_map_build_route_updates_api_map_payload(tmp_path: Path) -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    response = client.post(
        "/api/map/build",
        json={
            "project_path": str(project_root),
            "output": str(tmp_path / "outputs"),
        },
    )

    assert response.status_code == 200
    build_payload = response.json()
    assert build_payload["status"] == "ok"
    assert build_payload["viewer_load_result"]["loaded"] is True
    assert build_payload["viewer_load_result"]["graph_view_model"]["nodes"]

    api_payload = client.get("/api/map").json()
    fallback_payload = client.get("/map").json()
    assert api_payload == fallback_payload
    assert api_payload["viewer_load_result"]["loaded"] is True
    assert api_payload["viewer_load_result"]["graph_view_model"]["nodes"]


def test_map_payload_before_build_is_contract_compatible() -> None:
    client = TestClient(create_app())

    response = client.get("/api/map")

    assert response.status_code == 200
    payload = response.json()
    assert payload["viewer_load_result"]["loaded"] is False
    assert payload["viewer_load_result"]["error_reason"] == "no_map_loaded"
    assert payload["viewer_load_result"]["graph_view_model"]["nodes"] == []


def test_local_api_cors_does_not_use_wildcard_origin() -> None:
    app = create_app()

    cors_middleware = [
        item
        for item in app.user_middleware
        if getattr(item.cls, "__name__", "") == "CORSMiddleware"
    ]

    assert len(cors_middleware) == 1
    options = cast(dict[str, Any], cors_middleware[0].kwargs)
    origins = cast(list[str], options["allow_origins"])
    assert "*" not in origins
    assert "http://127.0.0.1:5173" in origins


def test_scan_events_returns_sse_completed_event() -> None:
    client = TestClient(create_app())

    with client.stream("GET", "/api/scan/events") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert "event: scan_progress" in body
    assert "data:" in body
    assert '"status":"completed"' in body
