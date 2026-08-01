from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from tests.helpers.fixtures import rag_project_fixture_path
from typer.testing import CliRunner

from systograph.cli import main as cli_main
from systograph.cli import map_command
from systograph.core.models.errors import (
    ScanInventoryRulesError,
    ScanInventoryRulesErrorCode,
)
from systograph.core.services.canonical_map_loader import (
    CanonicalMapLoader,
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
    map_markdown_path = tmp_path / "outputs" / "ai_system_map.md"
    profile_signals_path = tmp_path / "outputs" / "profile_signals.json"
    assert map_json_path.is_file()
    assert map_markdown_path.is_file()
    assert profile_signals_path.is_file()
    assert str(map_json_path) in result.stdout
    assert str(map_markdown_path) in result.stdout
    assert str(profile_signals_path) in result.stdout
    artifact_data = json.loads(map_json_path.read_text(encoding="utf-8"))
    loaded = CanonicalMapLoader().load(artifact_data)
    assert loaded.active_schema_version == "ai-system-map/v2"
    assert loaded.normalized.schema_version == "ai-system-map/v2"


def test_map_command_reports_missing_project_without_success_artifacts(
    tmp_path: Path,
) -> None:
    # Given
    output_dir = tmp_path / "outputs"

    # When
    result = CliRunner().invoke(
        cli_main.app,
        ["map", str(tmp_path / "missing"), "--output", str(output_dir)],
    )

    # Then
    assert result.exit_code == 1
    assert "Map build failed: project_path_not_found" in result.stderr
    assert f"Error report: {output_dir / 'map-error.md'}" in result.stderr
    assert (output_dir / "map-error.md").is_file()
    assert not (output_dir / "ai_system_map.json").exists()
    assert not (output_dir / "profile_signals.json").exists()


def test_map_command_is_thin_adapter_without_provider_logic() -> None:
    source = inspect.getsource(map_command)

    assert "MapBuildService" in source
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
    assert "ConfigParseProvider" not in source
    assert "DockerComposeProvider" not in source


def test_map_command_reports_inventory_catalog_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingMapBuildService:
        def build(self, request: object) -> object:
            del request
            raise ScanInventoryRulesError(ScanInventoryRulesErrorCode.INVALID)

    monkeypatch.setattr(
        map_command,
        "MapBuildService",
        FailingMapBuildService,
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(tmp_path),
            "--output",
            str(tmp_path / "outputs"),
        ],
    )

    assert result.exit_code == 1
    assert "Map build failed: inventory_rules_invalid" in result.stderr
    assert not (tmp_path / "outputs" / "ai_system_map.json").exists()


def test_map_command_rejects_public_v1_selection_without_artifacts(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(rag_project_fixture_path("basic_qdrant_ollama_rag")),
            "--output",
            str(output_dir),
            "--system-map-schema-version",
            "ai-system-map/v1",
        ],
    )

    assert result.exit_code == 1
    assert "legacy_output_not_selectable" in result.stderr
    assert not output_dir.exists()
