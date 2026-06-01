"""Build deterministic, read-only file inventories for scanner providers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Final

from pathspec import PathSpec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
    SkippedFile,
    SkipReason,
)

DEFAULT_MAX_FILE_SIZE_BYTES: Final = 1_000_000
BINARY_CHECK_BYTES: Final = 4096

DIRECTORY_SKIP_REASONS: Final[dict[str, SkipReason]] = {
    ".git": SkipReason.GIT_DIRECTORY,
    "node_modules": SkipReason.DEPENDENCY_DIRECTORY,
    ".venv": SkipReason.VIRTUAL_ENV,
    "venv": SkipReason.VIRTUAL_ENV,
    "dist": SkipReason.BUILD_OUTPUT,
    "build": SkipReason.BUILD_OUTPUT,
    "target": SkipReason.BUILD_OUTPUT,
    ".next": SkipReason.BUILD_OUTPUT,
    "__pycache__": SkipReason.CACHE_DIRECTORY,
    "coverage": SkipReason.COVERAGE_OUTPUT,
}
MODEL_WEIGHT_SUFFIXES: Final = {
    ".gguf",
    ".ggml",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
}
GENERATED_SUFFIXES: Final = {
    ".min.js",
    ".min.css",
}


class FilesystemProvider:
    """Create a scanner-safe project file inventory."""

    def __init__(
        self,
        *,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        git_executable: str = "git",
    ) -> None:
        self._max_file_size_bytes = max_file_size_bytes
        self._git_executable = git_executable

    def build_inventory(self, project_root: Path) -> FileInventory:
        root = project_root.resolve()
        if self._is_git_work_tree(root):
            try:
                return self._build_git_inventory(root)
            except (OSError, subprocess.SubprocessError) as exc:
                inventory = self._build_recursive_inventory(
                    root,
                    source=FileInventorySource.FALLBACK_AFTER_GIT_ERROR,
                )
                inventory.warnings.append(f"git inventory failed: {exc}")
                return inventory

        return self._build_recursive_inventory(
            root,
            source=FileInventorySource.RECURSIVE,
        )

    def normalize_project_relative_path(
        self,
        path: Path,
        *,
        project_root: Path,
    ) -> str:
        if path.is_absolute():
            root = project_root.resolve()
            try:
                relative = path.relative_to(root)
            except ValueError:
                relative = path.resolve().relative_to(root)
        else:
            relative = path
        return relative.as_posix().replace("\\", "/")

    def _build_git_inventory(self, root: Path) -> FileInventory:
        output = self._run_git(
            root,
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            ".",
        ).stdout
        git_paths = self._parse_nul_paths(output)
        files, skipped = self._classify_files(root, git_paths)
        skipped.extend(
            self._gitignored_files(root, included_paths=set(git_paths))
        )
        return FileInventory(
            source=FileInventorySource.GIT,
            project_root=str(root),
            files=files,
            skipped=self._sort_skipped(skipped),
        )

    def _build_recursive_inventory(
        self,
        root: Path,
        *,
        source: FileInventorySource,
    ) -> FileInventory:
        candidates, skipped = self._recursive_candidates(root)
        ignore_spec = self._load_gitignore_spec(root)
        visible_candidates = []
        for path in candidates:
            if ignore_spec is not None and ignore_spec.match_file(path):
                skipped.append(
                    SkippedFile(path=path, reason=SkipReason.GITIGNORED)
                )
                continue
            visible_candidates.append(path)

        files, file_skips = self._classify_files(root, visible_candidates)
        skipped.extend(file_skips)
        return FileInventory(
            source=source,
            project_root=str(root),
            files=files,
            skipped=self._sort_skipped(skipped),
        )

    def _is_git_work_tree(self, root: Path) -> bool:
        try:
            result = self._run_git(root, "rev-parse", "--is-inside-work-tree")
        except (OSError, subprocess.SubprocessError):
            return False
        return result.stdout.strip() == "true"

    def _run_git(
        self,
        root: Path,
        *args: str,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self._git_executable, *args],
            cwd=root,
            input=input_text,
            check=check,
            text=True,
            capture_output=True,
        )

    def _recursive_candidates(
        self,
        root: Path,
    ) -> tuple[list[str], list[SkippedFile]]:
        candidates: list[str] = []
        skipped: list[SkippedFile] = []
        for current_root, dirnames, filenames in os.walk(root, topdown=True):
            current = Path(current_root)
            kept_dirs = []
            for dirname in sorted(dirnames):
                child = current / dirname
                relative = self.normalize_project_relative_path(
                    child,
                    project_root=root,
                )
                reason = DIRECTORY_SKIP_REASONS.get(dirname)
                if reason is not None:
                    skipped.append(
                        SkippedFile(path=f"{relative}/", reason=reason)
                    )
                    continue
                if self._is_symlink_outside_root(child, root):
                    skipped.append(
                        SkippedFile(
                            path=f"{relative}/",
                            reason=SkipReason.SYMLINK_OUTSIDE_ROOT,
                        )
                    )
                    continue
                kept_dirs.append(dirname)
            dirnames[:] = kept_dirs

            for filename in sorted(filenames):
                path = current / filename
                if self._is_symlink_outside_root(path, root):
                    skipped.append(
                        SkippedFile(
                            path=self.normalize_project_relative_path(
                                path,
                                project_root=root,
                            ),
                            reason=SkipReason.SYMLINK_OUTSIDE_ROOT,
                        )
                    )
                    continue
                candidates.append(
                    self.normalize_project_relative_path(
                        path,
                        project_root=root,
                    )
                )
        return sorted(candidates), skipped

    def _classify_files(
        self,
        root: Path,
        relative_paths: list[str],
    ) -> tuple[list[FileRecord], list[SkippedFile]]:
        files: list[FileRecord] = []
        skipped: list[SkippedFile] = []
        for relative_path in sorted(set(relative_paths)):
            path = root / relative_path
            if not path.is_file():
                continue
            reason = self._skip_reason(path)
            size_bytes = self._safe_size(path)
            if reason is not None:
                skipped.append(
                    SkippedFile(
                        path=relative_path,
                        reason=reason,
                        size_bytes=size_bytes,
                    )
                )
                continue
            if size_bytes is None:
                skipped.append(
                    SkippedFile(
                        path=relative_path,
                        reason=SkipReason.UNREADABLE,
                    )
                )
                continue
            files.append(FileRecord(path=relative_path, size_bytes=size_bytes))
        return files, skipped

    def _skip_reason(self, path: Path) -> SkipReason | None:
        suffix = path.suffix.lower()
        name = path.name.lower()
        size_bytes = self._safe_size(path)
        if suffix in MODEL_WEIGHT_SUFFIXES:
            return SkipReason.MODEL_WEIGHT
        if any(name.endswith(suffix) for suffix in GENERATED_SUFFIXES):
            return SkipReason.GENERATED
        if size_bytes is not None and size_bytes > self._max_file_size_bytes:
            if suffix == ".log":
                return SkipReason.LARGE_LOG
            return SkipReason.LARGE_FILE
        if self._is_binary(path):
            return SkipReason.BINARY
        return None

    def _gitignored_files(
        self,
        root: Path,
        *,
        included_paths: set[str],
    ) -> list[SkippedFile]:
        candidates, _ = self._recursive_candidates(root)
        remaining = [path for path in candidates if path not in included_paths]
        if not remaining:
            return []

        input_text = "\0".join(remaining) + "\0"
        result = self._run_git(
            root,
            "check-ignore",
            "-z",
            "--stdin",
            input_text=input_text,
            check=False,
        )
        if result.returncode not in {0, 1}:
            return []
        return [
            SkippedFile(path=path, reason=SkipReason.GITIGNORED)
            for path in self._parse_nul_paths(result.stdout)
        ]

    def _load_gitignore_spec(
        self,
        root: Path,
    ) -> PathSpec[GitIgnoreBasicPattern] | None:
        gitignore_path = root / ".gitignore"
        if not gitignore_path.is_file():
            return None
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
        return PathSpec.from_lines("gitignore", lines)

    def _is_binary(self, path: Path) -> bool:
        try:
            with path.open("rb") as file:
                return b"\0" in file.read(BINARY_CHECK_BYTES)
        except OSError:
            return False

    def _safe_size(self, path: Path) -> int | None:
        try:
            return path.stat().st_size
        except OSError:
            return None

    def _is_symlink_outside_root(self, path: Path, root: Path) -> bool:
        if not path.is_symlink():
            return False
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return True
        return False

    def _parse_nul_paths(self, output: str) -> list[str]:
        return [path.replace("\\", "/") for path in output.split("\0") if path]

    def _sort_skipped(self, skipped: list[SkippedFile]) -> list[SkippedFile]:
        return sorted(skipped, key=lambda item: (item.path, item.reason.value))
