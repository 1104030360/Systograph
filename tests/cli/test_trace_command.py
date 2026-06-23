from __future__ import annotations

import inspect
import json
from pathlib import Path

from tests.unit.core.test_detail_scan_service import base_map
from typer.testing import CliRunner

from kai_mind.cli import main as cli_main
from kai_mind.cli import trace_command
from kai_mind.core.models.system_map import Endpoint


def test_trace_command_returns_endpoint_not_found_without_network(
    tmp_path: Path,
) -> None:
    map_path = tmp_path / "ai_system_map.json"
    map_path.write_text(base_map().model_dump_json(indent=2), encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "trace",
            str(map_path),
            "--endpoint-id",
            "endpoint:missing",
            "--query",
            "patient said sk-test-1234567890",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "endpoint_not_found"
    assert payload["query_sent"] is False
    assert "patient said" not in result.stdout
    assert "sk-test-1234567890" not in result.stdout


def test_trace_command_rejects_invalid_project_trace_config(
    tmp_path: Path,
) -> None:
    map_path = tmp_path / "ai_system_map.json"
    map_path.write_text(base_map().model_dump_json(indent=2), encoding="utf-8")
    project_root = tmp_path / "rag_project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        """
[tool.kai-mind.trace]
retrieved_chunks_keys = ["docs", ""]
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "trace",
            str(map_path),
            "--endpoint-id",
            "endpoint:missing",
            "--query",
            "hello",
            "--project-root",
            str(project_root),
        ],
    )

    assert result.exit_code == 1
    assert "invalid_trace_config" in result.stderr
    assert "retrieved_chunks_keys[1]" in result.stderr


def test_trace_command_blocks_unsafe_endpoint_without_network(
    tmp_path: Path,
) -> None:
    system_map = base_map()
    system_map.endpoints = [
        Endpoint(
            id="endpoint:metadata",
            value="http://169.254.169.254/latest/meta-data/",
            endpoint_type="local",
            method="GET",
            evidence_id="evidence:l1-router",
        )
    ]
    map_path = tmp_path / "ai_system_map.json"
    map_path.write_text(
        system_map.model_dump_json(indent=2),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "trace",
            str(map_path),
            "--endpoint-id",
            "endpoint:metadata",
            "--query",
            "private query",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["query_sent"] is False
    assert payload["error_reason"] == "egress_policy_blocked"
    assert [event["event_type"] for event in payload["events"]] == ["error"]
    assert "private query" not in result.stdout


def test_trace_command_is_thin_adapter_without_map_build_logic() -> None:
    source = inspect.getsource(trace_command)

    assert "QueryTraceService" in source
    assert "SystemMapValidationService" in source
    assert "MapBuildService" not in source
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
