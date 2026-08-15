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
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.canonical_map_loader import (
    CanonicalMapLoader,
)


def test_map_help_documents_non_interactive_boundary_gate() -> None:
    result = CliRunner().invoke(cli_main.app, ["map", "--help"])

    assert result.exit_code == 0
    assert "non-interactive inventory gate" in result.stdout
    assert "Web review flow" in result.stdout


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
            "--state-dir",
            str(tmp_path / "state"),
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


def test_map_command_runs_noninteractive_gate_and_persists_ua_snapshot(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    state_dir = tmp_path / "state"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(tmp_path / "outputs"),
            "--state-dir",
            str(state_dir),
        ],
    )

    assert result.exit_code == 0
    scan_id_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("scan_id=")
    )
    scan_id = scan_id_line.removeprefix("scan_id=")
    repository = LocalJsonStateProvider(state_dir)
    projects = repository.list_projects()
    assert len(projects) == 1
    snapshot = repository.get_snapshot(projects[0].project_id, scan_id)
    assert snapshot is not None
    assert snapshot.ua_analysis_result is not None
    assert snapshot.ua_analysis_result.semantic is None
    assert any(
        fact.provider == "understand_anything"
        for fact in snapshot.scan_result.facts
    )


def test_map_command_fails_closed_when_web_review_is_required(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("TOKEN=fixture\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(tmp_path / "outputs"),
            "--state-dir",
            str(tmp_path / "state"),
        ],
    )

    assert result.exit_code == 1
    assert "inventory_selection_noninteractive_review_required" in (
        result.stderr
    )
    assert "Web review" in result.stderr
    assert not (tmp_path / "outputs" / "ai_system_map.json").exists()


def test_map_command_reports_missing_project_without_success_artifacts(
    tmp_path: Path,
) -> None:
    # Given
    output_dir = tmp_path / "outputs"

    # When
    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(tmp_path / "missing"),
            "--output",
            str(output_dir),
            "--state-dir",
            str(tmp_path / "state"),
        ],
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

    assert "CliMapWorkflow" in source
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
    assert "ConfigParseProvider" not in source
    assert "DockerComposeProvider" not in source


def test_map_command_reports_inventory_catalog_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingMapWorkflow:
        def __init__(self, *, state_dir: Path, inventory_gate: object) -> None:
            del state_dir, inventory_gate

        def build(self, request: object) -> object:
            del request
            raise ScanInventoryRulesError(ScanInventoryRulesErrorCode.INVALID)

    monkeypatch.setattr(
        map_command,
        "CliMapWorkflow",
        FailingMapWorkflow,
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
            "--state-dir",
            str(tmp_path / "state"),
        ],
    )

    assert result.exit_code == 1
    assert "legacy_output_not_selectable" in result.stderr
    assert not output_dir.exists()


def test_map_command_refuses_a_legacy_operator_output_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI keeps the env fail-fast that only MapBuildService applies.

    Given SYSTOGRAPH_CANONICAL_OUTPUT_VERSION set to the removed v1 mode,
    When the map command runs,
    Then it refuses with invalid_canonical_output_version and writes no
    artifacts. The CLI has no startup hook of its own, so this guard only
    exists because MapBuildService validates the env on construction.
    """
    # Given
    output_dir = tmp_path / "outputs"
    monkeypatch.setenv(
        "SYSTOGRAPH_CANONICAL_OUTPUT_VERSION",
        "ai-system-map/v1",
    )

    # When
    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(rag_project_fixture_path("basic_qdrant_ollama_rag")),
            "--output",
            str(output_dir),
            "--state-dir",
            str(tmp_path / "state"),
        ],
    )

    # Then
    assert result.exit_code == 1
    assert "invalid_canonical_output_version" in result.stderr
    assert not output_dir.exists()


def test_map_command_approves_boundary_review_on_request(
    tmp_path: Path,
) -> None:
    # Given: the same project that fails closed without the flag.
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / ".env").write_text("TOKEN=fixture\n", encoding="utf-8")
    (project_root / "src" / "app.py").write_text(
        "from qdrant_client import QdrantClient\nclient = QdrantClient()\n",
        encoding="utf-8",
    )

    # When: the operator takes the boundary decision on the CLI instead
    # of in the Web review flow.
    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(tmp_path / "outputs"),
            "--state-dir",
            str(tmp_path / "state"),
            "--approve-boundary-review",
        ],
    )

    # Then: the scan completes and the decision is recorded as a
    # runtime user decision, exactly like the Web flow records it.
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (tmp_path / "outputs" / "ai_system_map.json").is_file()


def test_map_help_documents_the_boundary_approval_flag() -> None:
    result = CliRunner().invoke(cli_main.app, ["map", "--help"])

    assert result.exit_code == 0
    assert "--approve-boundary-review" in result.stdout


def test_map_command_surfaces_scan_warnings(tmp_path: Path) -> None:
    # Given: a project whose only component is detected from a compose
    # image, so its residence is a YAML file -- it can never be an edge
    # endpoint, and an empty graph should say so.
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "docker-compose.yml").write_text(
        "services:\n"
        "  qdrant:\n"
        "    image: qdrant/qdrant:v1.9.0\n"
        "    ports:\n"
        '      - "6333:6333"\n',
        encoding="utf-8",
    )
    (project_root / "src" / "app.py").write_text(
        "def serve() -> str:\n    return 'ok'\n", encoding="utf-8"
    )

    # When
    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(tmp_path / "outputs"),
            "--state-dir",
            str(tmp_path / "state"),
        ],
    )

    # Then: the operator can attribute an empty graph instead of
    # guessing why it is empty.
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "warning=UA edge derivation components with no code residence" in (
        result.stdout
    )
    assert "component:vector_store:qdrant" in result.stdout
