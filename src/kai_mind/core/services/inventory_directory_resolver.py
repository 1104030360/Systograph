from __future__ import annotations

import os
import stat
from pathlib import Path

from kai_mind.core.models.errors import InventoryEnumerationError
from kai_mind.core.models.inventory_selection import (
    DirectorySelectionManifest,
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryCandidateSet,
    InventoryRequestedTargetResult,
    InventoryRequestedTargetStatus,
    InventorySelectionSource,
    InventoryTargetKind,
)
from kai_mind.core.services.inventory_candidate_classifier import (
    InventoryCandidateClassifier,
)
from kai_mind.core.services.inventory_directory_walker import (
    InventoryDirectoryWalker,
)
from kai_mind.core.services.inventory_git_source_service import (
    InventoryGitSourceService,
)
from kai_mind.core.services.inventory_ignore_service import (
    InventoryIgnoreService,
)
from kai_mind.core.services.inventory_metadata_service import (
    InventoryMetadataService,
)


class InventoryDirectoryResolver:
    def __init__(
        self,
        *,
        classifier: InventoryCandidateClassifier,
        inventory_policy_digest: str,
        filesystem_safety_version: str,
        max_directory_files: int,
        max_directory_bytes: int,
        max_directory_depth: int,
        git_source_service: InventoryGitSourceService | None = None,
        ignore_service: InventoryIgnoreService | None = None,
        metadata_service: InventoryMetadataService | None = None,
    ) -> None:
        self._classifier = classifier
        self._inventory_policy_digest = inventory_policy_digest
        self._filesystem_safety_version = filesystem_safety_version
        self._git = git_source_service or InventoryGitSourceService()
        self._ignore = ignore_service or InventoryIgnoreService()
        self._metadata = metadata_service or InventoryMetadataService()
        self._walker = InventoryDirectoryWalker(
            classifier=classifier,
            max_files=max_directory_files,
            max_bytes=max_directory_bytes,
            max_depth=max_directory_depth,
            git_source_service=self._git,
            ignore_service=self._ignore,
        )

    def resolve(
        self,
        project_root: Path,
        path: str,
        *,
        candidate_set: InventoryCandidateSet,
    ) -> InventoryRequestedTargetResult:
        target = project_root if path == "." else project_root / path
        if path == ".git" or path.startswith(".git/"):
            return self._non_actionable(
                path,
                kind=InventoryTargetKind.DIRECTORY,
                status=InventoryRequestedTargetStatus.HARD_BLOCKED,
                reason="git_directory",
            )
        if self._contains_symlink_component(project_root, path):
            return self._non_actionable(
                path,
                kind=InventoryTargetKind.FILE,
                status=InventoryRequestedTargetStatus.HARD_BLOCKED,
                reason="symlink_not_allowed",
            )
        try:
            metadata = target.lstat()
        except FileNotFoundError:
            return self._non_actionable(
                path,
                kind=InventoryTargetKind.FILE,
                status=InventoryRequestedTargetStatus.MISSING,
                reason="inventory_selection_target_missing",
            )
        except OSError as exc:
            raise InventoryEnumerationError() from exc
        if stat.S_ISLNK(metadata.st_mode) or not (
            stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)
        ):
            return self._non_actionable(
                path,
                kind=InventoryTargetKind.FILE,
                status=InventoryRequestedTargetStatus.HARD_BLOCKED,
                reason="unsupported_file_type",
            )
        if stat.S_ISREG(metadata.st_mode):
            candidate = self._exact_file_candidate(
                project_root,
                path,
                metadata=metadata,
                candidate_set=candidate_set,
            )
            status = (
                InventoryRequestedTargetStatus.HARD_BLOCKED
                if candidate.base_outcome
                == InventoryCandidateOutcome.HARD_BLOCKED
                else InventoryRequestedTargetStatus.REVIEWABLE
            )
            return InventoryRequestedTargetResult(
                target_path=path,
                target_kind=InventoryTargetKind.FILE,
                status=status,
                file_candidate=(
                    candidate
                    if status == InventoryRequestedTargetStatus.REVIEWABLE
                    else None
                ),
                reason_code=(
                    candidate.reason_code
                    if status == InventoryRequestedTargetStatus.HARD_BLOCKED
                    else None
                ),
            )
        return self._resolve_directory(
            project_root,
            path,
            target=target,
            candidate_set=candidate_set,
        )

    def _resolve_directory(
        self,
        project_root: Path,
        path: str,
        *,
        target: Path,
        candidate_set: InventoryCandidateSet,
    ) -> InventoryRequestedTargetResult:
        walk_result = self._walker.walk(
            project_root,
            path,
            target,
            source_mode=candidate_set.source_mode,
        )
        if walk_result.limit_context is not None:
            return InventoryRequestedTargetResult(
                target_path=path,
                target_kind=InventoryTargetKind.DIRECTORY,
                status=(
                    InventoryRequestedTargetStatus.DIRECTORY_LIMIT_EXCEEDED
                ),
                reason_code=("inventory_selection_directory_limit_exceeded"),
                limit_context=walk_result.limit_context,
            )
        entries = walk_result.entries
        fingerprint = self._metadata.directory_manifest_fingerprint(
            directory_path=path,
            entries=entries,
            inventory_policy_digest=self._inventory_policy_digest,
            filesystem_safety_version=self._filesystem_safety_version,
        )
        manifest = DirectorySelectionManifest.from_entries(
            directory_path=path,
            entries=entries,
            manifest_fingerprint=fingerprint,
        )
        if manifest.selectable_file_count == 0:
            return self._non_actionable(
                path,
                kind=InventoryTargetKind.DIRECTORY,
                status=InventoryRequestedTargetStatus.EMPTY_DIRECTORY,
                reason="inventory_selection_directory_empty",
            )
        return InventoryRequestedTargetResult(
            target_path=path,
            target_kind=InventoryTargetKind.DIRECTORY,
            status=InventoryRequestedTargetStatus.REVIEWABLE,
            directory_manifest=manifest,
        )

    def _exact_file_candidate(
        self,
        project_root: Path,
        path: str,
        *,
        metadata: os.stat_result,
        candidate_set: InventoryCandidateSet,
    ) -> InventoryCandidate:
        existing = next(
            (item for item in candidate_set.candidates if item.path == path),
            None,
        )
        if existing is not None:
            return existing
        if candidate_set.source_mode == "git":
            source = self._git.ignore_sources(project_root, [path]).get(path)
        else:
            parent = (project_root / path).parent
            rules = self._ignore.rules_to_directory(project_root, parent)
            source = (
                InventorySelectionSource.PROJECT_IGNORE
                if self._ignore.is_ignored(path, rules)
                else None
            )
        return self._classifier.classify(
            path,
            metadata,
            exclusion_source=source,
        )

    def _non_actionable(
        self,
        path: str,
        *,
        kind: InventoryTargetKind,
        status: InventoryRequestedTargetStatus,
        reason: str,
    ) -> InventoryRequestedTargetResult:
        return InventoryRequestedTargetResult(
            target_path=path,
            target_kind=kind,
            status=status,
            reason_code=reason,
        )

    def _contains_symlink_component(
        self,
        project_root: Path,
        path: str,
    ) -> bool:
        if path == ".":
            return False
        current = project_root
        for part in Path(path).parts:
            current /= part
            try:
                if stat.S_ISLNK(current.lstat().st_mode):
                    return True
            except FileNotFoundError:
                return False
            except OSError as exc:
                raise InventoryEnumerationError() from exc
        return False
