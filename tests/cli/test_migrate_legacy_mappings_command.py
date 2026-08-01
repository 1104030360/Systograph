from __future__ import annotations

import json
from pathlib import Path

from tests.unit.core.test_legacy_manual_mapping_migration_service import (
    complete_legacy_payload,
    write_legacy_mapping,
)
from typer.testing import CliRunner

from systograph.cli import main as cli_main


def test_migration_cli_defaults_to_zero_write_dry_run(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    path = write_legacy_mapping(state_root, complete_legacy_payload())
    original = path.read_bytes()

    result = CliRunner().invoke(
        cli_main.app,
        ["migrate-legacy-mappings", "--state-dir", str(state_root)],
    )

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["status"] == "dry_run"
    assert report["converted"] == 1
    assert path.read_bytes() == original


def test_migration_cli_requires_explicit_apply_for_writes(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    path = write_legacy_mapping(state_root, complete_legacy_payload())

    result = CliRunner().invoke(
        cli_main.app,
        [
            "migrate-legacy-mappings",
            "--state-dir",
            str(state_root),
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "complete"
    assert json.loads(path.read_text(encoding="utf-8"))["mapping_type"] == (
        "non_baseline_capability_candidate"
    )
