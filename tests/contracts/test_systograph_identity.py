from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from systograph.web.app import default_state_dir

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_distribution_cli_and_package_use_only_systograph_identity() -> None:
    config = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert config["project"]["name"] == "systograph"
    assert config["project"]["scripts"] == {
        "systograph": "systograph.cli.main:main"
    }
    assert config["tool"]["hatch"]["build"]["targets"]["wheel"][
        "packages"
    ] == ["src/systograph"]
    assert config["tool"]["coverage"]["run"]["source"] == ["systograph"]
    assert (REPO_ROOT / "src" / "systograph" / "__init__.py").is_file()


def test_schema_ids_use_systograph_authority() -> None:
    for version in ("v1", "v2"):
        schema = json.loads(
            (
                REPO_ROOT / "schemas" / f"ai-system-map.{version}.schema.json"
            ).read_text(encoding="utf-8")
        )

        assert schema["$id"] == (
            "https://systograph.local/schemas/"
            f"ai-system-map.{version}.schema.json"
        )


def test_state_root_uses_systograph_environment_and_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configured = tmp_path / "state"
    monkeypatch.setenv("SYSTOGRAPH_STATE_DIR", str(configured))
    assert default_state_dir() == configured

    monkeypatch.delenv("SYSTOGRAPH_STATE_DIR")
    assert default_state_dir().name == ".systograph"
