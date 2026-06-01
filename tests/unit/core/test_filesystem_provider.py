from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from kai_mind.core.models.filesystem import (
    FileInventorySource,
    SkipReason,
)
from kai_mind.core.providers.filesystem_provider import FilesystemProvider


class FailingGitListProvider(FilesystemProvider):
    def _run_git(
        self,
        root: Path,
        *args: str,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if args[:1] == ("rev-parse",):
            return subprocess.CompletedProcess(
                args=["git", *args],
                returncode=0,
                stdout="true\n",
                stderr="",
            )
        if args[:1] == ("ls-files",):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *args],
                stderr="fatal: simulated git failure",
            )
        return super()._run_git(
            root,
            *args,
            input_text=input_text,
            check=check,
        )


def run_git(
    project_root: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        text=True,
        capture_output=True,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_inventory_includes_tracked_and_untracked_unignored_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    run_git(project_root, "init")
    (project_root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (project_root / "tracked.py").write_text(
        "tracked = True\n",
        encoding="utf-8",
    )
    run_git(project_root, "add", ".gitignore", "tracked.py")
    (project_root / "untracked.py").write_text(
        "untracked = True\n",
        encoding="utf-8",
    )
    (project_root / "ignored.py").write_text(
        "ignored = True\n",
        encoding="utf-8",
    )

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped_paths = {
        record.path: record.reason for record in inventory.skipped
    }
    assert inventory.source == FileInventorySource.GIT
    assert file_paths == {".gitignore", "tracked.py", "untracked.py"}
    assert skipped_paths["ignored.py"] == SkipReason.GITIGNORED
    assert all(not Path(path).is_absolute() for path in file_paths)


def test_recursive_inventory_for_non_git_zip_project_skips_noisy_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "zip-project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "node_modules" / "pkg").mkdir(parents=True)
    (project_root / ".venv").mkdir()
    (project_root / "dist").mkdir()
    (project_root / "models").mkdir()
    (project_root / "logs").mkdir()
    (project_root / "src" / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    (project_root / "node_modules" / "pkg" / "index.js").write_text(
        "module.exports = {};\n",
        encoding="utf-8",
    )
    (project_root / ".venv" / "pyvenv.cfg").write_text("", encoding="utf-8")
    (project_root / "dist" / "bundle.js").write_text(
        "x = 1;\n",
        encoding="utf-8",
    )
    (project_root / "models" / "llm.gguf").write_bytes(b"model")
    (project_root / "logs" / "scan.log").write_text(
        "x" * 40,
        encoding="utf-8",
    )
    (project_root / "binary.bin").write_bytes(b"abc\x00def")

    inventory = FilesystemProvider(max_file_size_bytes=16).build_inventory(
        project_root
    )

    assert inventory.source == FileInventorySource.RECURSIVE
    assert [record.path for record in inventory.files] == ["src/app.py"]
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert skipped["node_modules/"] == SkipReason.DEPENDENCY_DIRECTORY
    assert skipped[".venv/"] == SkipReason.VIRTUAL_ENV
    assert skipped["dist/"] == SkipReason.BUILD_OUTPUT
    assert skipped["models/llm.gguf"] == SkipReason.MODEL_WEIGHT
    assert skipped["logs/scan.log"] == SkipReason.LARGE_LOG
    assert skipped["binary.bin"] == SkipReason.BINARY


def test_recursive_inventory_honors_gitignore_double_star_rules(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "zip-project"
    (project_root / "docs" / "deep").mkdir(parents=True)
    (project_root / "nested").mkdir()
    (project_root / ".gitignore").write_text(
        "**/secret.env\ndocs/**/*.log\n",
        encoding="utf-8",
    )
    (project_root / "secret.env").write_text(
        "OPENAI_API_KEY=sk-test-example\n",
        encoding="utf-8",
    )
    (project_root / "nested" / "secret.env").write_text(
        "OPENAI_API_KEY=sk-test-example\n",
        encoding="utf-8",
    )
    (project_root / "docs" / "scan.log").write_text(
        "scan log\n",
        encoding="utf-8",
    )
    (project_root / "docs" / "deep" / "scan.log").write_text(
        "scan log\n",
        encoding="utf-8",
    )
    (project_root / "src.py").write_text("print('ok')\n", encoding="utf-8")

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert file_paths == {".gitignore", "src.py"}
    assert skipped["secret.env"] == SkipReason.GITIGNORED
    assert skipped["nested/secret.env"] == SkipReason.GITIGNORED
    assert skipped["docs/scan.log"] == SkipReason.GITIGNORED
    assert skipped["docs/deep/scan.log"] == SkipReason.GITIGNORED


def test_recursive_inventory_honors_nested_gitignore_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "zip-project"
    service_root = project_root / "service"
    (service_root / "sub").mkdir(parents=True)
    (service_root / ".gitignore").write_text(
        ".env\n*.local\n!keep.local\nsub/*.log\n",
        encoding="utf-8",
    )
    (service_root / ".env").write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (service_root / "settings.local").write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (service_root / "keep.local").write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (service_root / "sub" / "debug.log").write_text(
        "debug log\n",
        encoding="utf-8",
    )
    (service_root / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert file_paths == {
        "service/.gitignore",
        "service/app.py",
        "service/keep.local",
    }
    assert skipped["service/.env"] == SkipReason.GITIGNORED
    assert skipped["service/settings.local"] == SkipReason.GITIGNORED
    assert skipped["service/sub/debug.log"] == SkipReason.GITIGNORED


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_inventory_skips_tracked_symlink_to_file_outside_project(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.env"
    outside_file.write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (project_root / "outside.env").symlink_to(outside_file)
    run_git(project_root, "init")
    run_git(project_root, "add", "outside.env")

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert inventory.source == FileInventorySource.GIT
    assert "outside.env" not in file_paths
    assert skipped["outside.env"] == SkipReason.SYMLINK_OUTSIDE_ROOT


def test_path_normalization_outputs_project_relative_posix_paths(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    source_file = project_root / "src" / "api.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("from fastapi import FastAPI\n", encoding="utf-8")

    provider = FilesystemProvider()

    assert (
        provider.normalize_project_relative_path(
            source_file,
            project_root=project_root,
        )
        == "src/api.py"
    )
    assert (
        provider.normalize_project_relative_path(
            Path("src\\api.py"),
            project_root=project_root,
        )
        == "src/api.py"
    )


def test_git_listing_failure_falls_back_to_recursive_inventory(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "src" / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )

    inventory = FailingGitListProvider().build_inventory(project_root)

    assert inventory.source == FileInventorySource.FALLBACK_AFTER_GIT_ERROR
    assert [record.path for record in inventory.files] == ["src/app.py"]
    assert inventory.warnings


def test_symlink_to_file_outside_project_is_skipped(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside-secret.env"
    outside_file.write_text(
        "OPENAI_API_KEY=sk-test-example\n",
        encoding="utf-8",
    )
    (project_root / "outside.env").symlink_to(outside_file)

    inventory = FilesystemProvider().build_inventory(project_root)

    assert inventory.files == []
    assert inventory.skipped[0].path == "outside.env"
    assert inventory.skipped[0].reason == SkipReason.SYMLINK_OUTSIDE_ROOT


def test_provider_does_not_write_artifacts_to_project_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    before = sorted(path.name for path in project_root.iterdir())

    FilesystemProvider().build_inventory(project_root)

    after = sorted(path.name for path in project_root.iterdir())
    assert after == before
