from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from systograph.core.models.errors import PreconditionFailureReason
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)


def fixed_clock() -> datetime:
    return datetime(2026, 6, 1, 9, 30, 0, tzinfo=UTC)


def test_missing_project_returns_fatal_precondition_error(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    missing_project = tmp_path / "missing-project"
    output_dir = tmp_path / "outputs"

    result = provider.check_preconditions(
        project_path=missing_project,
        output_dir=output_dir,
    )

    assert not result.ok
    assert result.error is not None
    assert result.error.project_path == str(missing_project)
    assert (
        result.error.failure_reason
        == PreconditionFailureReason.PROJECT_PATH_NOT_FOUND
    )
    assert result.error.scan_stage == "precondition"
    assert result.project_root is None
    assert result.output_run is not None
    assert result.output_run.root_dir == output_dir.resolve()


def test_project_path_file_returns_not_directory_error(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    project_file = tmp_path / "not-a-directory.md"
    project_file.write_text("not a project directory", encoding="utf-8")

    result = provider.check_preconditions(
        project_path=project_file,
        output_dir=tmp_path / "outputs",
    )

    assert not result.ok
    assert result.error is not None
    assert (
        result.error.failure_reason
        == PreconditionFailureReason.PROJECT_PATH_NOT_DIRECTORY
    )


def test_unreadable_project_returns_not_readable_error(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    project_root = tmp_path / "unreadable-project"
    project_root.mkdir()
    original_mode = project_root.stat().st_mode

    try:
        project_root.chmod(0)
        if os.access(project_root, os.R_OK):
            pytest.skip("Current user can still read chmod(0) directory.")

        result = provider.check_preconditions(
            project_path=project_root,
            output_dir=tmp_path / "outputs",
        )

        assert not result.ok
        assert result.error is not None
        assert (
            result.error.failure_reason
            == PreconditionFailureReason.PROJECT_PATH_NOT_READABLE
        )
    finally:
        project_root.chmod(original_mode)


def test_project_root_without_search_permission_is_not_readable(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    project_root = tmp_path / "unsearchable-project"
    project_root.mkdir()
    original_mode = project_root.stat().st_mode

    try:
        project_root.chmod(0o400)
        if os.access(project_root, os.X_OK):
            pytest.skip("Current user can still search chmod(0400) directory.")

        result = provider.check_preconditions(
            project_path=project_root,
            output_dir=tmp_path / "outputs",
        )

        assert not result.ok
        assert result.error is not None
        assert (
            result.error.failure_reason
            == PreconditionFailureReason.PROJECT_PATH_NOT_READABLE
        )
    finally:
        project_root.chmod(original_mode)


def test_output_dir_without_search_permission_is_not_writable(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    project_root = tmp_path / "project"
    output_dir = tmp_path / "outputs"
    project_root.mkdir()
    output_dir.mkdir()
    original_mode = output_dir.stat().st_mode

    try:
        output_dir.chmod(0o200)
        if os.access(output_dir, os.X_OK):
            pytest.skip("Current user can still search chmod(0200) directory.")

        result = provider.check_preconditions(
            project_path=project_root,
            output_dir=output_dir,
        )

        assert not result.ok
        assert result.error is not None
        assert (
            result.error.failure_reason
            == PreconditionFailureReason.OUTPUT_DIRECTORY_NOT_WRITABLE
        )
    finally:
        output_dir.chmod(original_mode)


def test_readable_project_returns_normalized_root(tmp_path: Path) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    project_root = tmp_path / "project"
    output_dir = tmp_path / "outputs"
    project_root.mkdir()

    result = provider.check_preconditions(
        project_path=project_root,
        output_dir=output_dir,
    )

    assert result.ok
    assert result.error is None
    assert result.project_root == project_root.resolve()
    assert result.output_run is not None
    assert result.output_run.root_dir == output_dir.resolve()
    assert result.output_run.map_error_path == output_dir / "map-error.md"
    assert result.output_run.map_json_path == output_dir / "ai_system_map.json"
    assert result.output_run.map_markdown_path == (
        output_dir / "ai_system_map.md"
    )


def test_map_error_markdown_is_rendered_from_structured_error(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    missing_project = tmp_path / "missing-project"
    result = provider.check_preconditions(
        project_path=missing_project,
        output_dir=tmp_path / "outputs",
    )

    assert result.error is not None
    assert result.output_run is not None
    error_path = provider.write_map_error(
        result.error,
        output_run=result.output_run,
    )

    markdown = error_path.read_text(encoding="utf-8")
    assert error_path == tmp_path / "outputs" / "map-error.md"
    assert "scan_stage: precondition" in markdown
    assert f"project_path: {missing_project}" in markdown
    assert "failure_reason: project_path_not_found" in markdown
    assert "ai_system_map.json" not in markdown


def test_existing_map_artifact_uses_timestamped_run_directory(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    existing_map = output_dir / "ai_system_map.json"
    existing_map.write_text('{"existing": true}', encoding="utf-8")

    output_run = provider.prepare_output_run(output_dir)

    assert output_run.root_dir == output_dir / "20260601T093000"
    assert output_run.map_json_path == (
        output_dir / "20260601T093000" / "ai_system_map.json"
    )
    assert output_run.root_dir.is_dir()
    assert existing_map.read_text(encoding="utf-8") == '{"existing": true}'


def test_timestamp_collision_uses_deterministic_suffix(
    tmp_path: Path,
) -> None:
    provider = OutputArtifactProvider(clock=fixed_clock)
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    existing_map = output_dir / "ai_system_map.json"
    first_run_map = output_dir / "20260601T093000" / "ai_system_map.json"
    existing_map.write_text('{"existing": true}', encoding="utf-8")
    first_run_map.parent.mkdir()
    first_run_map.write_text('{"first_run": true}', encoding="utf-8")

    output_run = provider.prepare_output_run(output_dir)

    assert output_run.root_dir == output_dir / "20260601T093000-1"
    assert output_run.root_dir.is_dir()
    assert first_run_map.read_text(encoding="utf-8") == ('{"first_run": true}')
