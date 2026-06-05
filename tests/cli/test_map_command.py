from __future__ import annotations

import inspect
import json
from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path
from typer.testing import CliRunner

from kai_mind.cli import main as cli_main
from kai_mind.cli import map_command
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


def test_map_command_builds_same_canonical_artifact_contract(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    result = runner.invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(tmp_path / "outputs"),
        ],
    )

    assert result.exit_code == 0
    map_json_path = tmp_path / "outputs" / "ai_system_map.json"
    assert map_json_path.is_file()
    artifact_data = json.loads(map_json_path.read_text(encoding="utf-8"))
    assert (
        SystemMapValidationService().validate(artifact_data).schema_version
        == "ai-system-map/v1"
    )


def test_map_command_is_thin_adapter_without_provider_logic() -> None:
    source = inspect.getsource(map_command)

    assert "MapBuildService" in source
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
    assert "ConfigParseProvider" not in source
    assert "DockerComposeProvider" not in source
