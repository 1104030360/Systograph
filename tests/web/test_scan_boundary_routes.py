from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from kai_mind.web.app import create_app


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
    *,
    boundary_decisions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "project_id": project_id,
        "output": str(output),
    }
    if boundary_decisions is not None:
        payload["boundary_decisions"] = boundary_decisions
    response = client.post("/api/scans", json=payload)
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def test_scan_requires_boundary_decision_before_building_map(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = TestClient(create_app())
    project_id = import_project(client, project_root)
    before_map = client.get("/api/map").json()

    pending = scan_project(client, project_id, tmp_path / "outputs")

    assert pending["status"] == "requires_boundary_decision"
    assert pending["build_result"] is None
    assert pending["available_boundary_actions"] == [
        "scan_this_run",
        "skip_this_run",
    ]
    assert [
        item["target"]["path"] for item in pending["boundary_proposals"]
    ] == [".env"]
    proposal = pending["boundary_proposals"][0]
    assert proposal["status"] == "pending_user_confirmation"
    assert proposal["target"]["fingerprint"].startswith("sha256:")
    assert "sk-live-secret-value" not in str(pending)
    assert str(tmp_path) not in str(pending)
    assert client.get("/api/map").json() == before_map


def test_scan_this_run_decision_builds_map_for_current_scan_only(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = TestClient(create_app())
    project_id = import_project(client, project_root)
    pending = scan_project(client, project_id, tmp_path / "outputs")
    proposal = pending["boundary_proposals"][0]

    completed = scan_project(
        client,
        project_id,
        tmp_path / "outputs-2",
        boundary_decisions=[
            {
                "target_path": proposal["target"]["path"],
                "fingerprint": proposal["target"]["fingerprint"],
                "decision": "scan_this_run",
            }
        ],
    )
    next_scan = scan_project(client, project_id, tmp_path / "outputs-3")

    assert completed["status"] == "completed"
    assert completed["boundary_proposals"] == []
    assert (
        completed["build_result"]["ai_system_map"]["scan_summary"][
            "files_scanned"
        ]
        == 2
    )
    assert "sk-live-secret-value" not in str(completed)
    assert "OPENAI_API_KEY" in str(completed)
    assert next_scan["status"] == "requires_boundary_decision"
    assert next_scan["build_result"] is None


def test_skip_this_run_decision_builds_map_without_current_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = TestClient(create_app())
    project_id = import_project(client, project_root)
    pending = scan_project(client, project_id, tmp_path / "outputs")
    proposal = pending["boundary_proposals"][0]

    completed = scan_project(
        client,
        project_id,
        tmp_path / "outputs-2",
        boundary_decisions=[
            {
                "target_path": proposal["target"]["path"],
                "fingerprint": proposal["target"]["fingerprint"],
                "decision": "skip_this_run",
                "reason": "Skip this local config for the current scan.",
            }
        ],
    )

    assert completed["status"] == "completed"
    assert (
        completed["build_result"]["ai_system_map"]["scan_summary"][
            "files_scanned"
        ]
        == 1
    )
    assert (
        completed["build_result"]["ai_system_map"]["scan_summary"][
            "files_skipped"
        ]
        >= 1
    )
    assert "OPENAI_API_KEY" not in str(completed)
    assert "sk-live-secret-value" not in str(completed)


def test_scan_rejects_stale_or_removed_boundary_decisions(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    env_path = project_root / ".env"
    env_path.write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = TestClient(create_app())
    project_id = import_project(client, project_root)
    pending = scan_project(client, project_id, tmp_path / "outputs")
    proposal = pending["boundary_proposals"][0]
    env_path.write_text(
        "OPENAI_API_KEY=sk-different-value\n",
        encoding="utf-8",
    )

    stale = scan_project(
        client,
        project_id,
        tmp_path / "outputs-2",
        boundary_decisions=[
            {
                "target_path": proposal["target"]["path"],
                "fingerprint": proposal["target"]["fingerprint"],
                "decision": "scan_this_run",
            }
        ],
    )
    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs-3"),
            "boundary_decisions": [
                {
                    "target_path": ".env",
                    "fingerprint": proposal["target"]["fingerprint"],
                    "decision": "always_skip",
                }
            ],
        },
    )

    assert stale["status"] == "requires_boundary_decision"
    assert stale["build_result"] is None
    assert (
        stale["boundary_proposals"][0]["target"]["fingerprint"]
        != (proposal["target"]["fingerprint"])
    )
    assert response.status_code == 422
