from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from systograph.core.models.filesystem import FileInventorySource
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.git_environment import scoped_git_environment
from systograph.core.services.inventory_candidate_service import (
    InventoryCandidateService,
)
from systograph.core.services.inventory_git_source_service import (
    InventoryGitSourceService,
)


def make_git_repo(root: Path, *, tracked: str = "app.py") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / tracked).write_text("print('ok')\n", encoding="utf-8")
    env = scoped_git_environment()
    for args in (["init"], ["add", tracked]):
        subprocess.run(
            ["git", *args],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
        )


def test_scoped_environment_drops_repository_selection_variables() -> None:
    base = {
        "GIT_DIR": "/elsewhere/.git",
        "GIT_INDEX_FILE": "/elsewhere/.git/index",
        "GIT_WORK_TREE": "/elsewhere",
        "GIT_CONFIG_GLOBAL": "/elsewhere/.gitconfig",
        "PATH": "/usr/bin",
        "SYSTOGRAPH_STATE_DIR": "/state",
    }

    scoped = scoped_git_environment(base)

    assert scoped == {"PATH": "/usr/bin", "SYSTOGRAPH_STATE_DIR": "/state"}


def test_scoped_environment_defaults_to_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/elsewhere/.git")
    monkeypatch.setenv("SYSTOGRAPH_SENTINEL", "kept")

    scoped = scoped_git_environment()

    assert "GIT_DIR" not in scoped
    assert scoped["SYSTOGRAPH_SENTINEL"] == "kept"
    # The caller's own environment must not be mutated as a side effect.
    assert os.environ["GIT_DIR"] == "/elsewhere/.git"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_filesystem_provider_git_calls_resolve_to_the_target_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Probe the git seam directly rather than through the inventory.

    `build_inventory` reconciles `ls-files` output against the filesystem and
    drops paths that are not on disk, so a redirected enumeration still yields
    the target's files and hides the redirection. Asking git which repository
    it resolved is unambiguous.
    """

    target = tmp_path / "target"
    make_git_repo(target, tracked="app.py")
    unrelated = tmp_path / "unrelated"
    make_git_repo(unrelated, tracked="other.py")
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(unrelated / ".git" / "index"))

    resolved = (
        FilesystemProvider()
        ._run_git(target, "rev-parse", "--absolute-git-dir")
        .stdout.strip()
    )

    assert Path(resolved).resolve() == (target / ".git").resolve()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_inventory_stays_in_the_target_repo_when_git_dir_is_exported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end shape of the pre-commit hook case."""

    target = tmp_path / "target"
    make_git_repo(target, tracked="app.py")
    unrelated = tmp_path / "unrelated"
    make_git_repo(unrelated, tracked="other.py")
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(unrelated / ".git" / "index"))

    inventory = FilesystemProvider().build_inventory(target)

    assert inventory.source == FileInventorySource.GIT
    observed = {item.path for item in inventory.files}
    observed.update(item.path for item in inventory.skipped)
    assert observed == {"app.py"}


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_source_service_ignores_an_exported_git_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    make_git_repo(target, tracked="app.py")
    unrelated = tmp_path / "unrelated"
    make_git_repo(unrelated, tracked="other.py")
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))

    service = InventoryGitSourceService()

    assert service.is_work_tree(target) is True
    assert service.default_paths(target) == ["app.py"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_candidate_set_ignores_an_exported_git_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    make_git_repo(target, tracked="app.py")
    unrelated = tmp_path / "unrelated"
    make_git_repo(unrelated, tracked="other.py")
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))

    candidate_set = InventoryCandidateService().build_candidate_set(target)

    assert [item.path for item in candidate_set.candidates] == ["app.py"]


def test_suite_runs_without_inherited_git_variables() -> None:
    """Guards the autouse fixture in tests/conftest.py.

    Without it a suite started from `pre-commit` inherits GIT_DIR, and the
    `git init` / `git add` calls in the inventory fixtures act on this
    repository: they mark it bare and stage a truncated .gitignore.
    """

    assert [key for key in os.environ if key.startswith("GIT_")] == []
