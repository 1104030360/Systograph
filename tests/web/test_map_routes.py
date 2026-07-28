from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path
from tests.web.test_mapping_proposal_routes import (
    create_deterministic_test_app,
    import_and_scan_weak_project,
)

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


def test_map_report_route_returns_latest_markdown_report(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    build_response = client.post(
        "/api/map/build",
        json={
            "project_path": str(project_root),
            "output": str(tmp_path / "outputs"),
        },
    )
    report_response = client.get("/api/map/report")

    assert build_response.status_code == 200
    assert report_response.status_code == 200
    assert report_response.headers["content-type"].startswith("text/markdown")
    assert report_response.text.startswith("# KAI-Mind System Map\n")
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
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    client.post(
        "/api/map/build",
        json={
            "project_path": str(project_root),
            "output": str(tmp_path / "outputs"),
        },
    )

    response = client.get("/api/map/report?download=true")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="ai_system_map.md"'
    )


def test_map_build_route_rejects_public_v1_selection(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    client = TestClient(create_app())

    response = client.post(
        "/api/map/build",
        json={
            "project_path": str(
                rag_project_fixture_path("basic_qdrant_ollama_rag")
            ),
            "output": str(output_dir),
            "system_map_schema_version": "ai-system-map/v1",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "legacy_output_not_selectable"
    assert not output_dir.exists()


def test_map_report_route_before_build_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/api/map/report")

    assert response.status_code == 404
    assert response.json()["detail"] == "map_markdown_not_available"


def test_api_map_report_does_not_500_when_artifacts_are_tampered(
    tmp_path: Path,
) -> None:
    """artifact 被改壞時 /api/map/report 應回 404，不是 500。"""
    state_dir = tmp_path / "state"
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "chromadb==0.5.0\n",
        encoding="utf-8",
    )
    first = TestClient(create_app(state_dir=state_dir))
    project_id = first.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()["project_id"]
    scan = first.post(
        "/api/scans",
        json={"project_id": project_id, "output": str(tmp_path / "output")},
    ).json()
    Path(scan["build_result"]["map_json_path"]).write_text(
        "{}",
        encoding="utf-8",
    )

    # 重開 backend process：session cache 是空的，
    # 所以 report 一定得從磁碟 reload，才會踩到失效的 artifact。
    second = TestClient(
        create_app(state_dir=state_dir),
        raise_server_exceptions=False,
    )
    response = second.get("/api/map/report")

    assert response.status_code == 404
    assert response.json()["detail"] == "map_markdown_not_available"


def test_api_map_returns_newest_build_after_querying_an_older_project(
    tmp_path: Path,
) -> None:
    """查舊 project 的 mapping proposal 之後，/api/map 仍要回最新的 build。"""
    client = create_deterministic_test_app()
    older_id, older_unmapped_id = import_and_scan_weak_project(
        client,
        tmp_path,
        name="older_project",
        dependency="chromadb==0.5.0",
    )
    older_map = client.get("/api/map").json()
    older_build_id = older_map["viewer_load_result"]["ai_system_map"][
        "build_id"
    ]
    import_and_scan_weak_project(
        client,
        tmp_path,
        name="newer_project",
        dependency="qdrant-client==1.7.0",
    )
    newest = client.get("/api/map").json()
    newest_build_id = newest["viewer_load_result"]["ai_system_map"]["build_id"]
    assert newest_build_id != older_build_id

    proposal = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": older_id,
            "source_unmapped_id": older_unmapped_id,
        },
    )

    assert proposal.status_code == 200
    after = client.get("/api/map").json()
    assert after["viewer_load_result"]["ai_system_map"]["build_id"] == (
        newest_build_id
    )
    assert after == newest


def test_map_report_route_ignores_arbitrary_path_query(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    client.post(
        "/api/map/build",
        json={
            "project_path": str(project_root),
            "output": str(tmp_path / "outputs"),
        },
    )

    response = client.get("/api/map/report?path=/etc/passwd")

    assert response.status_code == 200
    assert response.text.startswith("# KAI-Mind System Map\n")
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
