from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PYTEST_STATE_ROOT = TemporaryDirectory(prefix="kai-mind-pytest-state-")
os.environ["KAI_MIND_STATE_DIR"] = PYTEST_STATE_ROOT.name


@pytest.fixture(autouse=True)
def isolate_default_state_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("KAI_MIND_STATE_DIR", str(tmp_path / "default-state"))
