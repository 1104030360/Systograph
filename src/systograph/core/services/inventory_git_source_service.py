from __future__ import annotations

import subprocess
from pathlib import Path

from systograph.core.models.inventory_selection import InventorySelectionSource
from systograph.core.services.path_safety_service import (
    PathSafetyError,
    normalize_project_relative_path,
)


class InventoryGitSourceService:
    def __init__(self, *, git_executable: str = "git") -> None:
        self._git_executable = git_executable

    def is_work_tree(self, root: Path) -> bool:
        try:
            result = self.run(root, "rev-parse", "--is-inside-work-tree")
        except (OSError, subprocess.SubprocessError):
            return False
        return result.stdout.strip() == "true"

    def default_paths(self, root: Path) -> list[str]:
        output = self.run(
            root,
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            ".",
        ).stdout
        return self.parse_paths(output)

    def ignored_paths(self, root: Path) -> list[tuple[str, bool]]:
        output = self.run(
            root,
            "ls-files",
            "-z",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--directory",
            "--",
            ".",
        ).stdout
        paths: list[tuple[str, bool]] = []
        for raw in output.split("\0"):
            if not raw:
                continue
            is_directory = raw.endswith("/")
            safe = self._safe_path(raw.rstrip("/"))
            if safe is not None:
                paths.append((safe, is_directory))
        return sorted(set(paths))

    def ignore_sources(
        self,
        root: Path,
        paths: list[str],
    ) -> dict[str, InventorySelectionSource]:
        if not paths:
            return {}
        result = self.run(
            root,
            "check-ignore",
            "-z",
            "-v",
            "--stdin",
            input_text="\0".join(paths) + "\0",
            check=False,
        )
        if result.returncode not in {0, 1}:
            return {
                path: InventorySelectionSource.PROJECT_IGNORE for path in paths
            }
        fields = result.stdout.split("\0")
        sources: dict[str, InventorySelectionSource] = {}
        for index in range(0, len(fields) - 3, 4):
            source_path, _line, _pattern, matched_path = fields[
                index : index + 4
            ]
            safe = self._safe_path(matched_path.rstrip("/"))
            if safe is None:
                continue
            sources[safe] = self._source_kind(source_path, root=root)
        return {
            path: sources.get(
                path,
                InventorySelectionSource.PROJECT_IGNORE,
            )
            for path in paths
        }

    def run(
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

    def parse_paths(self, output: str) -> list[str]:
        return sorted(
            {
                safe
                for raw in output.split("\0")
                if raw and (safe := self._safe_path(raw)) is not None
            }
        )

    def _source_kind(
        self,
        source_path: str,
        *,
        root: Path,
    ) -> InventorySelectionSource:
        normalized = source_path.replace("\\", "/")
        if normalized == ".git/info/exclude" or normalized.endswith(
            "/.git/info/exclude"
        ):
            return InventorySelectionSource.GIT_PRIVATE_EXCLUDE
        source = Path(source_path)
        if source.is_absolute():
            try:
                source.resolve().relative_to(root.resolve())
            except ValueError:
                return InventorySelectionSource.GIT_GLOBAL_EXCLUDE
        return InventorySelectionSource.PROJECT_IGNORE

    def _safe_path(self, path: str) -> str | None:
        try:
            return normalize_project_relative_path(path)
        except PathSafetyError:
            return None
