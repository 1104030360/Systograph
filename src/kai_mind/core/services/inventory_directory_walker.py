from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from kai_mind.core.models.errors import InventoryEnumerationError
from kai_mind.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryDirectoryLimitContext,
    InventoryDirectoryLimitKind,
    InventorySelectionSource,
)
from kai_mind.core.services.inventory_candidate_classifier import (
    InventoryCandidateClassifier,
)
from kai_mind.core.services.inventory_git_source_service import (
    InventoryGitSourceService,
)
from kai_mind.core.services.inventory_ignore_service import (
    InventoryIgnoreRules,
    InventoryIgnoreService,
)
from kai_mind.core.services.path_safety_service import (
    normalize_project_relative_path,
)


@dataclass(frozen=True, slots=True)
class InventoryDirectoryWalkResult:
    entries: tuple[InventoryCandidate, ...] = ()
    limit_context: InventoryDirectoryLimitContext | None = None


class InventoryDirectoryWalker:
    def __init__(
        self,
        *,
        classifier: InventoryCandidateClassifier,
        max_files: int,
        max_bytes: int,
        max_depth: int,
        git_source_service: InventoryGitSourceService,
        ignore_service: InventoryIgnoreService,
    ) -> None:
        self._classifier = classifier
        self._max_files = max_files
        self._max_bytes = max_bytes
        self._max_depth = max_depth
        self._git = git_source_service
        self._ignore = ignore_service

    def walk(
        self,
        project_root: Path,
        directory_path: str,
        target: Path,
        *,
        source_mode: Literal[
            "git",
            "recursive",
            "fallback_after_git_error",
        ],
    ) -> InventoryDirectoryWalkResult:
        raw: list[tuple[str, os.stat_result]] = []
        ignored: dict[str, bool] = {}
        rules_by_directory: dict[Path, tuple[InventoryIgnoreRules, ...]] = {
            target: self._ignore.rules_to_directory(project_root, target),
        }
        regular_count = 0
        for current_root, dirnames, filenames in os.walk(
            target,
            topdown=True,
            followlinks=False,
            onerror=self._raise_enumeration_error,
        ):
            current = Path(current_root)
            active_rules = rules_by_directory.get(current, ())
            dirnames[:] = self._prepare_directories(
                project_root,
                current,
                dirnames,
                active_rules=active_rules,
                rules_by_directory=rules_by_directory,
                raw=raw,
            )
            for filename in sorted(filenames):
                child = current / filename
                relative = normalize_project_relative_path(
                    child,
                    project_root=project_root,
                )
                metadata = child.lstat()
                raw.append((relative, metadata))
                ignored[relative] = self._ignore.is_ignored(
                    relative,
                    active_rules,
                )
                if stat.S_ISREG(metadata.st_mode):
                    regular_count += 1
                    if regular_count > self._max_files:
                        return self._limit(
                            InventoryDirectoryLimitKind.OBSERVED_FILE_COUNT,
                            self._max_files,
                            regular_count,
                        )
                depth = self._relative_depth(directory_path, relative)
                if depth > self._max_depth:
                    return self._limit(
                        InventoryDirectoryLimitKind.RELATIVE_DEPTH,
                        self._max_depth,
                        depth,
                    )
        entries = self._classify(
            project_root,
            raw,
            ignored=ignored,
            source_mode=source_mode,
        )
        selectable_bytes = sum(
            entry.size_bytes or 0
            for entry in entries
            if entry.base_outcome
            in {
                InventoryCandidateOutcome.INCLUDED,
                InventoryCandidateOutcome.SOFT_EXCLUDED,
            }
        )
        if selectable_bytes > self._max_bytes:
            return self._limit(
                InventoryDirectoryLimitKind.SELECTABLE_BYTES,
                self._max_bytes,
                selectable_bytes,
            )
        return InventoryDirectoryWalkResult(entries=entries)

    def _prepare_directories(
        self,
        project_root: Path,
        current: Path,
        dirnames: list[str],
        *,
        active_rules: tuple[InventoryIgnoreRules, ...],
        rules_by_directory: dict[
            Path,
            tuple[InventoryIgnoreRules, ...],
        ],
        raw: list[tuple[str, os.stat_result]],
    ) -> list[str]:
        kept: list[str] = []
        for dirname in sorted(dirnames):
            child = current / dirname
            relative = normalize_project_relative_path(
                child,
                project_root=project_root,
            )
            if relative == ".git" or relative.startswith(".git/"):
                continue
            metadata = child.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raw.append((relative, metadata))
                continue
            child_rules = active_rules
            loaded = self._ignore.load_for_directory(
                child,
                project_root=project_root,
            )
            if loaded is not None:
                child_rules = (*child_rules, loaded)
            rules_by_directory[child] = child_rules
            kept.append(dirname)
        return kept

    def _classify(
        self,
        project_root: Path,
        raw: list[tuple[str, os.stat_result]],
        *,
        ignored: dict[str, bool],
        source_mode: str,
    ) -> tuple[InventoryCandidate, ...]:
        git_sources = (
            self._git.ignore_sources(
                project_root,
                [relative for relative, _metadata in raw],
            )
            if source_mode == "git"
            else {}
        )
        return tuple(
            self._classifier.classify(
                relative,
                metadata,
                exclusion_source=(
                    git_sources.get(relative)
                    if source_mode == "git"
                    else (
                        InventorySelectionSource.PROJECT_IGNORE
                        if ignored.get(relative, False)
                        else None
                    )
                ),
            )
            for relative, metadata in raw
        )

    def _limit(
        self,
        kind: InventoryDirectoryLimitKind,
        limit: int,
        observed: int,
    ) -> InventoryDirectoryWalkResult:
        return InventoryDirectoryWalkResult(
            limit_context=InventoryDirectoryLimitContext(
                limit_kind=kind,
                limit=limit,
                observed_at_least=observed,
            )
        )

    def _relative_depth(self, directory: str, path: str) -> int:
        directory_parts = 0 if directory == "." else len(Path(directory).parts)
        return len(Path(path).parts) - directory_parts

    def _raise_enumeration_error(self, error: OSError) -> None:
        del error
        raise InventoryEnumerationError()
