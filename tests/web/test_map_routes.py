from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path
from tests.helpers.web_flows import scan_project

from systograph.web.app import create_app


def scan_fixture_project(
    client: TestClient,
    tmp_path: Path,
) -> dict[str, Any]:
    """Import the sample RAG project and scan it into `tmp_path`.

    Every map read below needs a committed build behind it, and the project
    session flow (`import` -> `scans`) is the only HTTP path that makes one.
    """

    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(
                rag_project_fixture_path("basic_qdrant_ollama_rag")
            ),
        },
    ).json()["project_id"]
    return scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )


def test_committed_scan_is_readable_from_process_wide_map_routes(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app())

    scan_payload = scan_fixture_project(client, tmp_path)

    assert scan_payload["status"] == "completed"
    build_payload = scan_payload["build_result"]
    assert build_payload["status"] == "ok"
    assert build_payload["viewer_load_result"]["loaded"] is True
    assert build_payload["viewer_load_result"]["graph_view_model"]["nodes"]

    api_payload = client.get("/api/map").json()
    fallback_payload = client.get("/map").json()
    assert api_payload == fallback_payload
    assert api_payload["viewer_load_result"]["loaded"] is True
    assert api_payload["viewer_load_result"]["graph_view_model"]["nodes"]


def test_map_report_route_returns_latest_markdown_report(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app())

    scan_fixture_project(client, tmp_path)
    report_response = client.get("/api/map/report")

    assert report_response.status_code == 200
    assert report_response.headers["content-type"].startswith("text/markdown")
    assert report_response.text.startswith("# Systograph System Map\n")
    assert "## Slot Coverage" in report_response.text
    assert "## Local Endpoints" in report_response.text
    assert "## External Endpoints" in report_response.text
    assert "## Network Exposure" in report_response.text
    assert "## Recommended Next Checks" in report_response.text
    assert "### Scan-fact checks" in report_response.text
    assert "### Capability review checks" in report_response.text
    assert "- No scan-fact checks." not in report_response.text
    assert "- [ ]" in report_response.text
    assert (
        "localhost:6333" in report_response.text
        or "6333" in report_response.text
    )


def test_map_report_route_can_return_download_attachment(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app())
    scan_fixture_project(client, tmp_path)

    response = client.get("/api/map/report?download=true")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="ai_system_map.md"'
    )


def test_map_report_route_before_build_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/api/map/report")

    assert response.status_code == 404
    assert response.json()["detail"] == "map_markdown_not_available"


def test_map_report_route_ignores_arbitrary_path_query(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app())
    scan_fixture_project(client, tmp_path)

    response = client.get("/api/map/report?path=/etc/passwd")

    assert response.status_code == 200
    assert response.text.startswith("# Systograph System Map\n")
    assert "root:" not in response.text


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

    origins = app.allowed_origins
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
