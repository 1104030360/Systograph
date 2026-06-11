from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from kai_mind.core.services.scan_boundary_review_service import (
    InMemoryScanBoundaryRepository,
    ScanBoundaryReviewService,
)
from kai_mind.web.app import create_app


def create_test_client() -> TestClient:
    return TestClient(
        create_app(
            scan_boundary_review_service=ScanBoundaryReviewService(
                repository=InMemoryScanBoundaryRepository()
            )
        )
    )


def import_project(client: TestClient, project_root: Path) -> str:
    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )
    assert response.status_code == 200
    return str(response.json()["project_id"])


def scan_project(
    client: TestClient,
    project_id: str,
    output: Path,
) -> dict[str, Any]:
    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(output),
        },
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def test_scan_boundary_routes_create_list_decide_and_apply_next_scan(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = create_test_client()
    project_id = import_project(client, project_root)
    first_scan = scan_project(client, project_id, tmp_path / "outputs")
    before_map = client.get("/api/map").json()

    create_response = client.post(
        "/api/scan-boundary-proposals",
        json={"project_id": project_id},
    )
    after_map = client.get("/api/map").json()

    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["project_id"] == project_id
    assert payload["available_actions"] == [
        "skip_this_run",
        "always_skip",
        "metadata_only",
        "masked_summary_only",
        "scan_normally",
    ]
    assert [
        proposal["target"]["path"] for proposal in payload["proposals"]
    ] == [".env"]
    proposal = payload["proposals"][0]
    assert proposal["status"] == "pending_user_confirmation"
    assert proposal["target"]["fingerprint"].startswith("sha256:")
    assert "sk-live-secret-value" not in str(payload)
    assert str(tmp_path) not in str(payload)
    assert after_map == before_map

    list_response = client.get(
        f"/api/scan-boundary-proposals?project_id={project_id}"
    )
    assert list_response.status_code == 200
    assert (
        list_response.json()["proposals"][0]["proposal_id"]
        == (proposal["proposal_id"])
    )

    decision_response = client.post(
        f"/api/scan-boundary-proposals/{proposal['proposal_id']}/decision",
        json={
            "decision": "always_skip",
            "reason": "Local-only secret config.",
        },
    )

    assert decision_response.status_code == 200
    decision_payload = decision_response.json()
    assert decision_payload["proposal"]["status"] == "decided"
    assert decision_payload["decision"]["decision"] == "always_skip"
    assert "sk-live-secret-value" not in str(decision_payload)
    assert (
        (project_root / ".env")
        .read_text(encoding="utf-8")
        .startswith("OPENAI_API_KEY=")
    )

    second_scan = scan_project(client, project_id, tmp_path / "outputs-2")
    assert (
        first_scan["build_result"]["ai_system_map"]["scan_summary"][
            "files_scanned"
        ]
        == 1
    )
    assert (
        first_scan["build_result"]["ai_system_map"]["scan_summary"][
            "files_skipped"
        ]
        >= 1
    )
    assert (
        second_scan["build_result"]["ai_system_map"]["scan_summary"][
            "files_scanned"
        ]
        == 1
    )
    assert (
        second_scan["build_result"]["ai_system_map"]["scan_summary"][
            "files_skipped"
        ]
        >= 1
    )


def test_scan_normally_decision_allows_next_scan_to_parse_secret_like_config(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = create_test_client()
    project_id = import_project(client, project_root)
    first_scan = scan_project(client, project_id, tmp_path / "outputs")
    create_response = client.post(
        "/api/scan-boundary-proposals",
        json={"project_id": project_id},
    )
    proposal = create_response.json()["proposals"][0]

    decision_response = client.post(
        f"/api/scan-boundary-proposals/{proposal['proposal_id']}/decision",
        json={
            "decision": "scan_normally",
            "reason": "Approved for normal config parsing.",
        },
    )
    second_scan = scan_project(client, project_id, tmp_path / "outputs-2")

    assert decision_response.status_code == 200
    assert (
        first_scan["build_result"]["ai_system_map"]["scan_summary"][
            "files_scanned"
        ]
        == 1
    )
    assert (
        second_scan["build_result"]["ai_system_map"]["scan_summary"][
            "files_scanned"
        ]
        == 2
    )
    assert "sk-live-secret-value" not in str(second_scan)
    assert "OPENAI_API_KEY" in str(second_scan)


def test_scan_boundary_create_requires_existing_project() -> None:
    client = create_test_client()

    response = client.post(
        "/api/scan-boundary-proposals",
        json={"project_id": "project:missing"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "project_not_found"


def test_scan_boundary_create_requires_loaded_map(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    client = create_test_client()
    project_id = import_project(client, project_root)

    response = client.post(
        "/api/scan-boundary-proposals",
        json={"project_id": project_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "map_not_loaded"


def test_scan_boundary_decision_missing_proposal_returns_404() -> None:
    client = create_test_client()

    response = client.post(
        "/api/scan-boundary-proposals/proposal:missing/decision",
        json={"decision": "scan_normally", "reason": "No such proposal."},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "proposal_not_found"
