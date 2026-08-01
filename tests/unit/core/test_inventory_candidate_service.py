from __future__ import annotations

import os
import shutil
import subprocess
from errno import EACCES, EPERM
from pathlib import Path
from typing import IO, Any, cast

import pytest

from systograph.core.models.errors import InventorySelectionError
from systograph.core.models.inventory_selection import (
    InventoryCandidateOutcome,
    InventoryDirectoryLimitKind,
    InventoryRequestedTargetStatus,
    InventorySelectionSource,
)
from systograph.core.services.inventory_candidate_service import (
    InventoryCandidateService,
)


def run_git(project_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        capture_output=True,
    )


def symlink_or_skip(
    link_path: Path,
    target_path: Path,
    *,
    target_is_directory: bool = False,
) -> None:
    try:
        link_path.symlink_to(
            target_path,
            target_is_directory=target_is_directory,
        )
    except OSError as exc:
        if (
            exc.errno in {EACCES, EPERM}
            or getattr(exc, "winerror", None) == 1314
        ):
            pytest.skip("symlink privilege is unavailable on this platform")
        raise


def test_recursive_candidates_keep_file_exclusions_and_collapse_directories(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "ignored-dir").mkdir()
    (project_root / "node_modules" / "pkg").mkdir(parents=True)
    (project_root / ".gitignore").write_text(
        "ignored.py\nignored-dir/\nmissing.env\n",
        encoding="utf-8",
    )
    (project_root / "src" / "app.py").write_text("app\n", encoding="utf-8")
    (project_root / "ignored.py").write_text("ignored\n", encoding="utf-8")
    (project_root / "ignored-dir" / "data.txt").write_text(
        "ignored\n",
        encoding="utf-8",
    )
    (project_root / "node_modules" / "pkg" / "index.js").write_text(
        "module\n",
        encoding="utf-8",
    )

    candidate_set = InventoryCandidateService().build_candidate_set(
        project_root
    )

    candidates = {item.path: item for item in candidate_set.candidates}
    summaries = {item.path: item for item in candidate_set.skipped_summaries}
    assert candidates["src/app.py"].base_outcome == (
        InventoryCandidateOutcome.INCLUDED
    )
    assert candidates["ignored.py"].base_outcome == (
        InventoryCandidateOutcome.SOFT_EXCLUDED
    )
    assert candidates["ignored.py"].exclusion_sources == (
        InventorySelectionSource.PROJECT_IGNORE,
    )
    assert set(summaries) == {"ignored-dir", "node_modules"}
    assert "missing.env" not in candidates
    assert candidate_set.candidate_set_digest.startswith("sha256:")


def test_exact_directory_expands_soft_excluded_descendants_and_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "node_modules" / "pkg").mkdir(parents=True)
    (project_root / ".git" / "objects").mkdir(parents=True)
    (project_root / "node_modules" / "pkg" / "index.js").write_text(
        "module\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("app\n", encoding="utf-8")
    (project_root / ".git" / "objects" / "internal").write_text(
        "git-internal\n",
        encoding="utf-8",
    )
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    directory = service.resolve_requested_path(
        project_root,
        "node_modules",
        candidate_set=candidate_set,
    )
    root = service.resolve_requested_path(
        project_root,
        ".",
        candidate_set=candidate_set,
    )

    assert directory.status == InventoryRequestedTargetStatus.REVIEWABLE
    assert directory.directory_manifest is not None
    assert [item.path for item in directory.directory_manifest.entries] == [
        "node_modules/pkg/index.js"
    ]
    assert directory.directory_manifest.soft_excluded_count == 1
    assert directory.directory_manifest.manifest_fingerprint.startswith(
        "sha256:"
    )
    assert root.status == InventoryRequestedTargetStatus.REVIEWABLE
    assert root.target_path == "."
    assert root.directory_manifest is not None
    assert all(
        not item.path.startswith(".git/")
        for item in root.directory_manifest.entries
    )


def test_exact_missing_and_git_internal_paths_are_not_actionable(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".git").mkdir(parents=True)
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    missing = service.resolve_requested_path(
        project_root,
        "missing.py",
        candidate_set=candidate_set,
    )
    git_internal = service.resolve_requested_path(
        project_root,
        ".git",
        candidate_set=candidate_set,
    )

    assert missing.status == InventoryRequestedTargetStatus.MISSING
    assert missing.reason_code == "inventory_selection_target_missing"
    assert git_internal.status == InventoryRequestedTargetStatus.HARD_BLOCKED
    assert git_internal.reason_code == "git_directory"


def test_exact_path_through_symlinked_parent_is_hard_blocked(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    outside = tmp_path / "outside"
    project_root.mkdir()
    outside.mkdir()
    (outside / "secret.py").write_text("outside\n", encoding="utf-8")
    symlink_or_skip(
        project_root / "linked",
        outside,
        target_is_directory=True,
    )
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    result = service.resolve_requested_path(
        project_root,
        "linked/secret.py",
        candidate_set=candidate_set,
    )

    assert result.status == InventoryRequestedTargetStatus.HARD_BLOCKED
    assert result.reason_code == "symlink_not_allowed"


@pytest.mark.parametrize(
    "invalid",
    ["", "/absolute.py", "../outside.py", "src/*.py", "src/[ab].py"],
)
def test_requested_paths_use_project_relative_posix_exact_contract(
    invalid: str,
) -> None:
    service = InventoryCandidateService()

    assert service.normalize_requested_path(r"src\app.py") == "src/app.py"
    with pytest.raises(InventorySelectionError) as exc_info:
        service.normalize_requested_path(invalid)
    assert str(exc_info.value) == "inventory_selection_path_invalid"


def test_directory_limits_return_non_actionable_result(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    target = project_root / "many"
    target.mkdir(parents=True)
    for index in range(3):
        (target / f"{index}.py").write_text("x\n", encoding="utf-8")
    service = InventoryCandidateService(max_directory_files=2)
    candidate_set = service.build_candidate_set(project_root)

    result = service.resolve_requested_path(
        project_root,
        "many",
        candidate_set=candidate_set,
    )

    assert result.status == (
        InventoryRequestedTargetStatus.DIRECTORY_LIMIT_EXCEEDED
    )
    assert result.directory_manifest is None
    assert result.limit_context is not None
    assert result.limit_context.limit_kind == "observed_file_count"
    assert result.limit_context.observed_at_least == 3


def test_directory_file_limit_allows_5000_and_rejects_5001(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    target = project_root / "ignored"
    target.mkdir(parents=True)
    (project_root / ".gitignore").write_text(
        "ignored/\n",
        encoding="utf-8",
    )
    for index in range(5_000):
        (target / f"{index:04d}.py").touch()
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    at_limit = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )
    (target / "5000.py").touch()
    over_limit = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )

    assert at_limit.status == InventoryRequestedTargetStatus.REVIEWABLE
    assert at_limit.directory_manifest is not None
    assert at_limit.directory_manifest.observed_regular_file_count == 5_000
    assert over_limit.status == (
        InventoryRequestedTargetStatus.DIRECTORY_LIMIT_EXCEEDED
    )
    assert over_limit.limit_context is not None
    assert over_limit.limit_context.limit_kind == (
        InventoryDirectoryLimitKind.OBSERVED_FILE_COUNT
    )
    assert over_limit.limit_context.observed_at_least == 5_001


def test_directory_byte_limit_allows_500m_and_rejects_500m_plus_one(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    target = project_root / "ignored"
    target.mkdir(parents=True)
    (project_root / ".gitignore").write_text(
        "ignored/\n",
        encoding="utf-8",
    )
    for index in range(5):
        with (target / f"{index}.py").open("wb") as handle:
            handle.truncate(100_000_000)
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    at_limit = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )
    (target / "plus-one.py").write_bytes(b"x")
    over_limit = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )

    assert at_limit.status == InventoryRequestedTargetStatus.REVIEWABLE
    assert at_limit.directory_manifest is not None
    assert at_limit.directory_manifest.selectable_bytes == 500_000_000
    assert over_limit.status == (
        InventoryRequestedTargetStatus.DIRECTORY_LIMIT_EXCEEDED
    )
    assert over_limit.limit_context is not None
    assert over_limit.limit_context.limit_kind == (
        InventoryDirectoryLimitKind.SELECTABLE_BYTES
    )
    assert over_limit.limit_context.observed_at_least == 500_000_001


def test_directory_depth_limit_allows_64_and_rejects_65(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    target = project_root / "ignored"
    target.mkdir(parents=True)
    (project_root / ".gitignore").write_text(
        "ignored/\n",
        encoding="utf-8",
    )
    current = target
    for index in range(63):
        current /= f"d{index:02d}"
        current.mkdir()
    (current / "at-limit.py").touch()
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    at_limit = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )
    over = current / "d63"
    over.mkdir()
    (over / "over-limit.py").touch()
    over_limit = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )

    assert at_limit.status == InventoryRequestedTargetStatus.REVIEWABLE
    assert at_limit.directory_manifest is not None
    assert at_limit.directory_manifest.observed_max_relative_depth == 64
    assert over_limit.status == (
        InventoryRequestedTargetStatus.DIRECTORY_LIMIT_EXCEEDED
    )
    assert over_limit.limit_context is not None
    assert over_limit.limit_context.limit_kind == (
        InventoryDirectoryLimitKind.RELATIVE_DEPTH
    )
    assert over_limit.limit_context.observed_at_least == 65


def test_directory_with_only_hard_blocked_children_is_empty(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    target = project_root / "ignored"
    target.mkdir(parents=True)
    (project_root / ".gitignore").write_text(
        "ignored/\n",
        encoding="utf-8",
    )
    symlink_or_skip(target / "linked.py", tmp_path / "outside.py")
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    result = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )

    assert result.status == InventoryRequestedTargetStatus.EMPTY_DIRECTORY
    assert result.directory_manifest is None
    assert result.reason_code == "inventory_selection_directory_empty"


def test_special_file_is_hard_blocked_for_exact_and_directory_selection(
    tmp_path: Path,
) -> None:
    mkfifo = getattr(os, "mkfifo", None)
    if not callable(mkfifo):
        pytest.skip("FIFO is unavailable")

    project_root = tmp_path / "project"
    target = project_root / "ignored"
    target.mkdir(parents=True)
    (project_root / ".gitignore").write_text(
        "ignored/\n",
        encoding="utf-8",
    )
    fifo = target / "events.pipe"
    mkfifo(fifo)
    service = InventoryCandidateService()
    candidate_set = service.build_candidate_set(project_root)

    exact = service.resolve_requested_path(
        project_root,
        "ignored/events.pipe",
        candidate_set=candidate_set,
    )
    directory = service.resolve_requested_path(
        project_root,
        "ignored",
        candidate_set=candidate_set,
    )

    assert exact.status == InventoryRequestedTargetStatus.HARD_BLOCKED
    assert exact.reason_code == "unsupported_file_type"
    assert directory.status == InventoryRequestedTargetStatus.EMPTY_DIRECTORY


def test_candidate_preflight_does_not_open_candidate_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    candidate_path = project_root / "app.py"
    candidate_path.write_text("do not read\n", encoding="utf-8")
    original_open = Path.open

    def guarded_open(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> IO[Any]:
        if path == candidate_path:
            raise AssertionError("candidate content was opened")
        return cast(IO[Any], original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", guarded_open)

    candidate_set = InventoryCandidateService().build_candidate_set(
        project_root
    )

    assert [item.path for item in candidate_set.candidates] == ["app.py"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_candidate_sources_do_not_expose_global_exclude_path(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    excludes = tmp_path / "private-global-excludes"
    excludes.write_text("global.py\n", encoding="utf-8")
    run_git(project_root, "init")
    run_git(project_root, "config", "core.excludesFile", str(excludes))
    (project_root / "global.py").write_text("global\n", encoding="utf-8")

    candidate_set = InventoryCandidateService().build_candidate_set(
        project_root
    )

    candidate = next(
        item for item in candidate_set.candidates if item.path == "global.py"
    )
    assert candidate.exclusion_sources == (
        InventorySelectionSource.GIT_GLOBAL_EXCLUDE,
    )
    assert str(excludes) not in candidate_set.model_dump_json()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_tracked_but_missing_is_a_non_actionable_candidate(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    run_git(project_root, "init")
    tracked = project_root / "tracked.py"
    tracked.write_text("tracked\n", encoding="utf-8")
    run_git(project_root, "add", "tracked.py")
    tracked.unlink()
    (project_root / "app.py").write_text("app\n", encoding="utf-8")

    candidate_set = InventoryCandidateService().build_candidate_set(
        project_root
    )

    candidates = {item.path: item for item in candidate_set.candidates}
    assert candidates["tracked.py"].base_outcome == (
        InventoryCandidateOutcome.MISSING
    )
    assert candidates["tracked.py"].reason_code == "missing_at_scan"
    assert candidates["tracked.py"].override_allowed is False
    assert candidates["app.py"].base_outcome == (
        InventoryCandidateOutcome.INCLUDED
    )
    assert candidate_set.warnings == ("tracked_missing_candidate_observed",)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_private_exclude_is_typed_without_exposing_source_path(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    run_git(project_root, "init")
    (project_root / ".git" / "info" / "exclude").write_text(
        "private.py\n",
        encoding="utf-8",
    )
    (project_root / "private.py").write_text("private\n", encoding="utf-8")

    candidate_set = InventoryCandidateService().build_candidate_set(
        project_root
    )

    candidate = next(
        item for item in candidate_set.candidates if item.path == "private.py"
    )
    assert candidate.exclusion_sources == (
        InventorySelectionSource.GIT_PRIVATE_EXCLUDE,
    )
    assert ".git/info/exclude" not in candidate_set.model_dump_json()
