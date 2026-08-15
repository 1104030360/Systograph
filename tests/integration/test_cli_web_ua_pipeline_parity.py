from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path
from tests.helpers.web_flows import create_scan_with_preflight
from typer.testing import CliRunner

from systograph.cli import main as cli_main
from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.web.app import create_app


def project_neutral_scan_payload(snapshot: ScanSnapshot) -> dict[str, object]:
    payload = snapshot.scan_result.model_dump(mode="json")
    payload.pop("final_inventory_digest")
    payload.pop("inventory_run_digest")
    for entry in payload["inventory_policy_audit"]:
        entry.pop("preflight_request_id")
    return payload


def test_cli_and_web_persist_equivalent_ua_scan_results(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    web_state = tmp_path / "web-state"
    cli_state = tmp_path / "cli-state"
    web_client = TestClient(create_app(state_dir=web_state))
    project_id = web_client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()["project_id"]
    web_response = create_scan_with_preflight(
        web_client,
        project_id,
        output=str(tmp_path / "web-output"),
    )
    assert web_response.status_code == 200
    web_scan_id = web_response.json()["scan_id"]

    cli_result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(tmp_path / "cli-output"),
            "--state-dir",
            str(cli_state),
        ],
    )
    assert cli_result.exit_code == 0
    cli_scan_id = next(
        line.removeprefix("scan_id=")
        for line in cli_result.stdout.splitlines()
        if line.startswith("scan_id=")
    )

    web_snapshot = LocalJsonStateProvider(web_state).get_snapshot(
        project_id,
        web_scan_id,
    )
    cli_repository = LocalJsonStateProvider(cli_state)
    cli_project = cli_repository.list_projects()[0]
    cli_snapshot = cli_repository.get_snapshot(
        cli_project.project_id,
        cli_scan_id,
    )
    assert web_snapshot is not None
    assert cli_snapshot is not None
    assert project_neutral_scan_payload(web_snapshot) == (
        project_neutral_scan_payload(cli_snapshot)
    )
    assert web_snapshot.ua_analysis_result == cli_snapshot.ua_analysis_result
