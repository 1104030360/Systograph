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

PYTEST_STATE_ROOT = TemporaryDirectory(prefix="systograph-pytest-state-")
os.environ["SYSTOGRAPH_STATE_DIR"] = PYTEST_STATE_ROOT.name


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
    monkeypatch.setenv("SYSTOGRAPH_STATE_DIR", str(tmp_path / "default-state"))


@pytest.fixture(autouse=True)
def isolate_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep git subprocesses inside their own fixture repository.

    Git exports ``GIT_DIR`` and ``GIT_INDEX_FILE`` to every hook it runs, so a
    suite started from ``pre-commit`` inherits them. Any ``git`` a test spawns
    then resolves against this repository instead of its ``tmp_path`` fixture:
    ``git init`` re-initialises this repo (and marks it bare), ``ls-files``
    reports this repo's tracked files, and ``git add`` writes this repo's
    index. Clearing the namespace keeps a hook-run suite honest.
    """

    for name in [key for key in os.environ if key.startswith("GIT_")]:
        monkeypatch.delenv(name, raising=False)
