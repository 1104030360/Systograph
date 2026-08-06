"""Build deterministic, read-only file inventories for scanner providers."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pathspec import GitIgnoreSpec

from systograph.core.models.errors import InventoryEnumerationError
from systograph.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
    SkippedFile,
    SkipReason,
)
from systograph.core.models.inventory_policy import (
    InventoryPolicyAction,
)
from systograph.core.services.git_environment import scoped_git_environment
from systograph.core.services.inventory_policy_matcher import (
    InventoryPolicyMatch,
    InventoryPolicyMatcher,
)
from systograph.core.services.inventory_provenance_service import (
    InventoryProvenanceService,
)
from systograph.core.services.path_safety_service import (
    PathSafetyError,
    normalize_project_relative_path,
)
from systograph.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)

DEFAULT_MAX_FILE_SIZE_BYTES: Final = 1_000_000
BINARY_CHECK_BYTES: Final = 4096


@dataclass(frozen=True)
class _GitIgnoreRules:
    base_path: str
    spec: GitIgnoreSpec


class FilesystemProvider:
    """Create a scanner-safe project file inventory."""

    def __init__(
        self,
        *,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        git_executable: str = "git",
        inventory_rule_loader: ScanInventoryRuleLoader | None = None,
    ) -> None:
        self._max_file_size_bytes = max_file_size_bytes
        self._git_executable = git_executable
        self._inventory_rule_loader = (
            inventory_rule_loader or ScanInventoryRuleLoader()
        )
        self._provenance_service = InventoryProvenanceService()

    @property
    def inventory_rule_loader(self) -> ScanInventoryRuleLoader:
        return self._inventory_rule_loader

    def build_inventory(self, project_root: Path) -> FileInventory:
        catalog = self._inventory_rule_loader.load_default()
        matcher = InventoryPolicyMatcher(catalog)
        root = project_root.resolve()
        if self._is_git_work_tree(root):
            try:
                inventory = self._build_git_inventory(root, matcher=matcher)
            except (OSError, subprocess.SubprocessError):
                inventory = self._build_recursive_inventory(
                    root,
                    source=FileInventorySource.FALLBACK_AFTER_GIT_ERROR,
                    matcher=matcher,
                )
                inventory.warnings.append(
                    "git_enumeration_failed_fallback_used"
                )
        else:
            inventory = self._build_recursive_inventory(
                root,
                source=FileInventorySource.RECURSIVE,
                matcher=matcher,
            )
        return self._provenance_service.finalize(
            inventory,
            catalog=catalog,
            matcher=matcher,
        )

    def normalize_project_relative_path(
        self,
        path: Path,
        *,
        project_root: Path,
    ) -> str:
        return normalize_project_relative_path(
            path,
            project_root=project_root,
        )

    def _build_git_inventory(
        self,
        root: Path,
        *,
        matcher: InventoryPolicyMatcher,
    ) -> FileInventory:
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
        files, skipped = self._classify_files(
            root,
            git_paths,
            matcher=matcher,
        )
        skipped.extend(
            self._gitignored_files(
                root,
                included_paths=set(git_paths),
                matcher=matcher,
            )
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
        matcher: InventoryPolicyMatcher,
    ) -> FileInventory:
        candidates, skipped = self._recursive_candidates(
            root,
            matcher=matcher,
        )
        files, file_skips = self._classify_files(
            root,
            candidates,
            matcher=matcher,
        )
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
            env=scoped_git_environment(),
            input=input_text,
            check=check,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            capture_output=True,
        )

    def _recursive_candidates(
        self,
        root: Path,
        *,
        matcher: InventoryPolicyMatcher,
    ) -> tuple[list[str], list[SkippedFile]]:
        candidates: list[str] = []
        skipped: list[SkippedFile] = []
        active_rules_by_dir: dict[Path, tuple[_GitIgnoreRules, ...]] = {
            root: (),
        }
        for current_root, dirnames, filenames in os.walk(
            root,
            topdown=True,
            onerror=self._raise_enumeration_error,
        ):
            current = Path(current_root)
            active_rules = active_rules_by_dir.get(current, ())
            current_gitignore = current / ".gitignore"
            if not self._is_symlink_outside_root(current_gitignore, root):
                loaded_rules = self._load_gitignore_rules(
                    current_gitignore,
                    base_path=self.normalize_project_relative_path(
                        current,
                        project_root=root,
                    )
                    if current != root
                    else "",
                )
                if loaded_rules is not None:
                    active_rules = (*active_rules, loaded_rules)

            kept_dirs = []
            for dirname in sorted(dirnames):
                child = current / dirname
                relative = self.normalize_project_relative_path(
                    child,
                    project_root=root,
                )
                if self._is_symlink_outside_root(child, root):
                    skipped.append(
                        SkippedFile(
                            path=f"{relative}/",
                            reason=SkipReason.SYMLINK_OUTSIDE_ROOT,
                        )
                    )
                    continue
                if dirname == ".git":
                    skipped.append(
                        SkippedFile(
                            path=f"{relative}/",
                            reason=SkipReason.GIT_DIRECTORY,
                        )
                    )
                    continue
                policy_match = matcher.match(relative, is_directory=True)
                policy_reason = self._catalog_skip_reason(policy_match)
                if policy_reason is not None and not matcher.has_include_rules:
                    skipped.append(
                        SkippedFile(
                            path=f"{relative}/",
                            reason=policy_reason,
                        )
                    )
                    continue
                if self._is_gitignored(f"{relative}/", active_rules):
                    skipped.append(
                        SkippedFile(
                            path=f"{relative}/",
                            reason=SkipReason.GITIGNORED,
                        )
                    )
                    continue
                active_rules_by_dir[child] = active_rules
                kept_dirs.append(dirname)
            dirnames[:] = kept_dirs

            for filename in sorted(filenames):
                path = current / filename
                relative = self.normalize_project_relative_path(
                    path,
                    project_root=root,
                )
                if self._is_symlink_outside_root(path, root):
                    skipped.append(
                        SkippedFile(
                            path=relative,
                            reason=SkipReason.SYMLINK_OUTSIDE_ROOT,
                        )
                    )
                    continue
                if self._is_gitignored(relative, active_rules):
                    skipped.append(
                        SkippedFile(
                            path=relative,
                            reason=SkipReason.GITIGNORED,
                        )
                    )
                    continue
                candidates.append(relative)
        return sorted(candidates), skipped

    def _classify_files(
        self,
        root: Path,
        relative_paths: list[str],
        *,
        matcher: InventoryPolicyMatcher,
    ) -> tuple[list[FileRecord], list[SkippedFile]]:
        files: list[FileRecord] = []
        skipped: list[SkippedFile] = []
        for relative_path in sorted(set(relative_paths)):
            path = root / relative_path
            if self._is_symlink_outside_root(path, root):
                skipped.append(
                    SkippedFile(
                        path=relative_path,
                        reason=SkipReason.SYMLINK_OUTSIDE_ROOT,
                    )
                )
                continue
            if not path.is_file():
                continue
            reason = self._skip_reason(
                path,
                relative_path=relative_path,
                matcher=matcher,
            )
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

    def _skip_reason(
        self,
        path: Path,
        *,
        relative_path: str,
        matcher: InventoryPolicyMatcher,
    ) -> SkipReason | None:
        suffix = path.suffix.lower()
        policy_match = matcher.match(relative_path)
        policy_reason = self._catalog_skip_reason(policy_match)
        if policy_reason is not None:
            return policy_reason
        size_bytes = self._safe_size(path)
        if size_bytes is not None and size_bytes > self._max_file_size_bytes:
            if suffix == ".log":
                return SkipReason.LARGE_LOG
            return SkipReason.LARGE_FILE
        if self._is_binary(path):
            return SkipReason.BINARY
        return None

    def _catalog_skip_reason(
        self,
        policy_match: InventoryPolicyMatch,
    ) -> SkipReason | None:
        if policy_match.effective_action != InventoryPolicyAction.EXCLUDE:
            return None
        if policy_match.effective_reason is None:
            return None
        return SkipReason(policy_match.effective_reason)

    def _gitignored_files(
        self,
        root: Path,
        *,
        included_paths: set[str],
        matcher: InventoryPolicyMatcher,
    ) -> list[SkippedFile]:
        candidates, recursive_skipped = self._recursive_candidates(
            root,
            matcher=matcher,
        )
        skipped = [
            record
            for record in recursive_skipped
            if record.reason == SkipReason.GITIGNORED
        ]
        remaining = [path for path in candidates if path not in included_paths]
        if not remaining:
            return skipped

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
            return skipped
        skipped_paths = {record.path for record in skipped}
        skipped.extend(
            SkippedFile(path=path, reason=SkipReason.GITIGNORED)
            for path in self._parse_nul_paths(result.stdout)
            if path not in skipped_paths
        )
        return skipped

    def _load_gitignore_rules(
        self,
        gitignore_path: Path,
        *,
        base_path: str,
    ) -> _GitIgnoreRules | None:
        if not gitignore_path.is_file():
            return None
        try:
            lines = gitignore_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise InventoryEnumerationError() from exc
        return _GitIgnoreRules(
            base_path=base_path,
            spec=GitIgnoreSpec.from_lines(lines),
        )

    def _is_gitignored(
        self,
        relative_path: str,
        rules: tuple[_GitIgnoreRules, ...],
    ) -> bool:
        ignored = False
        for rule_set in rules:
            path_for_rule = self._relative_to_gitignore_base(
                relative_path,
                rule_set.base_path,
            )
            if path_for_rule is None:
                continue
            result = rule_set.spec.check_file(path_for_rule)
            if result.include is not None:
                ignored = result.include
        return ignored

    def _relative_to_gitignore_base(
        self,
        relative_path: str,
        base_path: str,
    ) -> str | None:
        if not base_path:
            return relative_path
        prefix = f"{base_path}/"
        if not relative_path.startswith(prefix):
            return None
        return relative_path.removeprefix(prefix)

    def _is_binary(self, path: Path) -> bool:
        try:
            with path.open("rb") as file:
                return b"\0" in file.read(BINARY_CHECK_BYTES)
        except OSError:
            return False

    def _raise_enumeration_error(self, error: OSError) -> None:
        del error
        raise InventoryEnumerationError()

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
        paths: list[str] = []
        for path in output.split("\0"):
            if not path:
                continue
            try:
                paths.append(normalize_project_relative_path(path))
            except PathSafetyError:
                continue
        return paths

    def _sort_skipped(self, skipped: list[SkippedFile]) -> list[SkippedFile]:
        return sorted(skipped, key=lambda item: (item.path, item.reason.value))
