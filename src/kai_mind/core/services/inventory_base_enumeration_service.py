from __future__ import annotations

import os
import stat
from pathlib import Path

from kai_mind.core.models.errors import InventoryEnumerationError
from kai_mind.core.models.inventory_policy import InventoryPolicyAction
from kai_mind.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryDirectorySummary,
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


class InventoryBaseEnumerationService:
    def __init__(
        self,
        *,
        git_source_service: InventoryGitSourceService,
        ignore_service: InventoryIgnoreService,
    ) -> None:
        self._git = git_source_service
        self._ignore = ignore_service

    def git_candidates(
        self,
        root: Path,
        *,
        classifier: InventoryCandidateClassifier,
    ) -> tuple[list[InventoryCandidate], list[InventoryDirectorySummary]]:
        candidates = {
            path: classifier.classify(
                path,
                self._lstat_or_missing(root / path),
            )
            for path in self._git.default_paths(root)
        }
        ignored_paths = self._git.ignored_paths(root)
        sources = self._git.ignore_sources(
            root,
            [path for path, _is_directory in ignored_paths],
        )
        summaries: list[InventoryDirectorySummary] = []
        for path, is_directory in ignored_paths:
            source = sources.get(
                path,
                InventorySelectionSource.PROJECT_IGNORE,
            )
            if is_directory:
                summaries.append(
                    InventoryDirectorySummary(
                        path=path,
                        reason_code="gitignored",
                        exclusion_source=source,
                    )
                )
                continue
            candidates.setdefault(
                path,
                classifier.classify(
                    path,
                    self._lstat(root / path),
                    exclusion_source=source,
                ),
            )
        return list(candidates.values()), summaries

    def recursive_candidates(
        self,
        root: Path,
        *,
        classifier: InventoryCandidateClassifier,
    ) -> tuple[list[InventoryCandidate], list[InventoryDirectorySummary]]:
        candidates: list[InventoryCandidate] = []
        summaries: list[InventoryDirectorySummary] = []
        root_rules = self._ignore.load_for_directory(root, project_root=root)
        rules_by_directory: dict[Path, tuple[InventoryIgnoreRules, ...]] = {
            root: (root_rules,) if root_rules is not None else (),
        }
        for current_root, dirnames, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
            onerror=self._raise_enumeration_error,
        ):
            current = Path(current_root)
            active_rules = rules_by_directory.get(current, ())
            kept_dirs: list[str] = []
            for dirname in sorted(dirnames):
                child = current / dirname
                relative = normalize_project_relative_path(
                    child,
                    project_root=root,
                )
                metadata = self._lstat(child)
                if relative == ".git" or stat.S_ISLNK(metadata.st_mode):
                    summaries.append(
                        self._hard_directory_summary(
                            relative,
                            is_git=relative == ".git",
                        )
                    )
                    continue
                policy_match = classifier.matcher.match(
                    relative,
                    is_directory=True,
                )
                ignored = self._ignore.is_ignored(
                    f"{relative}/",
                    active_rules,
                )
                policy_excluded = (
                    policy_match.effective_action
                    == InventoryPolicyAction.EXCLUDE
                )
                if ignored or (
                    policy_excluded
                    and not classifier.matcher.has_include_rules
                ):
                    summaries.append(
                        InventoryDirectorySummary(
                            path=relative,
                            reason_code=(
                                "gitignored"
                                if ignored
                                else policy_match.effective_reason
                                or "catalog_excluded"
                            ),
                            exclusion_source=(
                                InventorySelectionSource.PROJECT_IGNORE
                                if ignored
                                else (
                                    InventorySelectionSource.KAI_INVENTORY_CATALOG
                                )
                            ),
                        )
                    )
                    continue
                rules_by_directory[child] = self._child_rules(
                    child,
                    root=root,
                    active_rules=active_rules,
                )
                kept_dirs.append(dirname)
            dirnames[:] = kept_dirs
            candidates.extend(
                self._file_candidate(
                    current / filename,
                    root=root,
                    active_rules=active_rules,
                    classifier=classifier,
                )
                for filename in sorted(filenames)
            )
        return candidates, summaries

    def _file_candidate(
        self,
        path: Path,
        *,
        root: Path,
        active_rules: tuple[InventoryIgnoreRules, ...],
        classifier: InventoryCandidateClassifier,
    ) -> InventoryCandidate:
        relative = normalize_project_relative_path(path, project_root=root)
        source = (
            InventorySelectionSource.PROJECT_IGNORE
            if self._ignore.is_ignored(relative, active_rules)
            else None
        )
        return classifier.classify(
            relative,
            self._lstat(path),
            exclusion_source=source,
        )

    def _child_rules(
        self,
        child: Path,
        *,
        root: Path,
        active_rules: tuple[InventoryIgnoreRules, ...],
    ) -> tuple[InventoryIgnoreRules, ...]:
        loaded = self._ignore.load_for_directory(
            child,
            project_root=root,
        )
        return (*active_rules, loaded) if loaded is not None else active_rules

    def _hard_directory_summary(
        self,
        path: str,
        *,
        is_git: bool,
    ) -> InventoryDirectorySummary:
        return InventoryDirectorySummary(
            path=path,
            reason_code=("git_directory" if is_git else "symlink_not_allowed"),
            exclusion_source=InventorySelectionSource.FILESYSTEM_SAFETY,
            can_expand=False,
        )

    def _lstat(self, path: Path) -> os.stat_result:
        try:
            return path.lstat()
        except OSError as exc:
            raise InventoryEnumerationError() from exc

    def _lstat_or_missing(self, path: Path) -> os.stat_result | None:
        try:
            return path.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise InventoryEnumerationError() from exc

    def _raise_enumeration_error(self, error: OSError) -> None:
        del error
        raise InventoryEnumerationError()
