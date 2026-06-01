from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)


def fixed_clock() -> datetime:
    return datetime(2026, 6, 1, 9, 30, 0, tzinfo=UTC)


def test_missing_project_writes_only_map_error_artifact(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    output_dir = tmp_path / "outputs"
    missing_project = tmp_path / "missing-project"

    result = provider.check_preconditions(
        project_path=missing_project,
        output_dir=output_dir,
    )
    assert result.error is not None
    assert result.output_run is not None

    provider.write_map_error(result.error, output_run=result.output_run)

    assert (output_dir / "map-error.md").is_file()
    assert not (output_dir / "ai_system_map.json").exists()
    assert not (output_dir / "ai_system_map.md").exists()


def test_existing_outputs_are_not_overwritten_for_next_run(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    project_root = tmp_path / "project"
    output_dir = tmp_path / "outputs"
    project_root.mkdir()
    output_dir.mkdir()
    existing_map = output_dir / "ai_system_map.json"
    existing_summary = output_dir / "ai_system_map.md"
    existing_map.write_text('{"existing": true}', encoding="utf-8")
    existing_summary.write_text("# Existing report\n", encoding="utf-8")

    result = provider.check_preconditions(
        project_path=project_root,
        output_dir=output_dir,
    )

    assert result.ok
    assert result.output_run is not None
    assert result.output_run.root_dir == output_dir / "20260601T093000"
    assert result.output_run.map_json_path == (
        output_dir / "20260601T093000" / "ai_system_map.json"
    )
    assert existing_map.read_text(encoding="utf-8") == '{"existing": true}'
    assert existing_summary.read_text(encoding="utf-8") == (
        "# Existing report\n"
    )
