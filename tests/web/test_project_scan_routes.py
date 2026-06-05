from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.web.app import create_app


def test_project_import_accepts_only_local_path_source() -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"].startswith("project:")
    assert payload["source_type"] == "local_path"
    assert payload["project_name"] == "basic_qdrant_ollama_rag"


def test_project_import_rejects_upload_source_type() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "upload",
            "project_path": "/tmp/example.zip",
        },
    )

    assert response.status_code == 422


def test_scan_create_builds_imported_project(tmp_path: Path) -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    import_response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )
    project_id = import_response.json()["project_id"]

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "scan_depth": "system",
            "output": str(tmp_path / "outputs"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scan_id"].startswith("scan:")
    assert payload["project_id"] == project_id
    assert payload["status"] == "completed"
    assert payload["build_result"]["status"] == "ok"


def test_scan_create_rejects_unknown_project() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/scans",
        json={
            "project_id": "project:missing",
            "scan_depth": "system",
        },
    )

    assert response.status_code == 404
