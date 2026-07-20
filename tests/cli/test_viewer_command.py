from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from kai_mind.cli import main as cli_main
from kai_mind.cli import viewer_command

FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
INVALID_FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/invalid_confidence.v1.json"
)


def test_validate_map_command_reports_valid_graph_load() -> None:
    result = CliRunner().invoke(
        cli_main.app,
        ["validate-map", str(FIXTURE_PATH)],
    )

    assert result.exit_code == 0
    assert "loaded=true" in result.output
    assert "nodes=" in result.output
    assert "edges=" in result.output


def test_validate_map_command_reports_invalid_map_error() -> None:
    result = CliRunner().invoke(
        cli_main.app,
        ["validate-map", str(INVALID_FIXTURE_PATH)],
    )

    assert result.exit_code == 1
    assert "loaded=false" in result.output
    assert "confidence" in result.output


def test_validate_map_help_describes_dual_read_contract() -> None:
    result = CliRunner().invoke(cli_main.app, ["validate-map", "--help"])

    assert result.exit_code == 0
    assert "ai-system-map/v1 or ai-system-map/v2" in result.output


def test_validate_map_command_is_thin_adapter_without_provider_logic() -> None:
    source = inspect.getsource(viewer_command)

    assert "ViewerSessionService" in source
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
    assert "ConfigParseProvider" not in source
    assert "DockerComposeProvider" not in source
