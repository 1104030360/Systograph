from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
TEST_DIRECTORY_MARKERS: Final[frozenset[str]] = frozenset(
    {"cli", "contracts", "e2e", "integration", "unit", "web"}
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PYTEST_STATE_ROOT = TemporaryDirectory(prefix="kai-mind-pytest-state-")
os.environ["KAI_MIND_STATE_DIR"] = PYTEST_STATE_ROOT.name


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        relative_path = item.path.relative_to(TEST_ROOT)
        directory = relative_path.parts[0]
        if directory in TEST_DIRECTORY_MARKERS:
            marker = "contract" if directory == "contracts" else directory
            item.add_marker(marker)
        elif relative_path.name == "test_smoke.py":
            item.add_marker("smoke")


@pytest.fixture(autouse=True)
def isolate_default_state_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("KAI_MIND_STATE_DIR", str(tmp_path / "default-state"))
