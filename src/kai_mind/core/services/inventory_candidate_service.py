from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final, Literal

from kai_mind.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from kai_mind.core.models.inventory_selection import (
    InventoryCandidateOutcome,
    InventoryCandidateSet,
    InventoryRequestedTargetResult,
)
from kai_mind.core.services.inventory_base_enumeration_service import (
    InventoryBaseEnumerationService,
)
from kai_mind.core.services.inventory_candidate_classifier import (
    DEFAULT_ABSOLUTE_MAX_FILE_BYTES,
    DEFAULT_LARGE_FILE_REVIEW_BYTES,
    InventoryCandidateClassifier,
)
from kai_mind.core.services.inventory_directory_resolver import (
    InventoryDirectoryResolver,
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
from kai_mind.core.services.inventory_policy_matcher import (
    InventoryPolicyMatcher,
)
from kai_mind.core.services.inventory_provenance_service import (
    FILESYSTEM_SAFETY_VERSION,
)
from kai_mind.core.services.path_safety_service import (
    PathSafetyError,
    normalize_project_relative_path,
)
from kai_mind.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)

MAX_RECURSIVE_DIRECTORY_FILES: Final = 5_000
MAX_RECURSIVE_DIRECTORY_BYTES: Final = 500_000_000
MAX_RECURSIVE_DIRECTORY_DEPTH: Final = 64


class InventoryCandidateService:
    def __init__(
        self,
        *,
        inventory_rule_loader: ScanInventoryRuleLoader | None = None,
        git_source_service: InventoryGitSourceService | None = None,
        default_large_file_review_bytes: int = (
            DEFAULT_LARGE_FILE_REVIEW_BYTES
        ),
        absolute_max_file_bytes: int = DEFAULT_ABSOLUTE_MAX_FILE_BYTES,
        max_directory_files: int = MAX_RECURSIVE_DIRECTORY_FILES,
        max_directory_bytes: int = MAX_RECURSIVE_DIRECTORY_BYTES,
        max_directory_depth: int = MAX_RECURSIVE_DIRECTORY_DEPTH,
    ) -> None:
        self._loader = inventory_rule_loader or ScanInventoryRuleLoader()
        self._git = git_source_service or InventoryGitSourceService()
        self._ignore = InventoryIgnoreService()
        self._enumeration = InventoryBaseEnumerationService(
            git_source_service=self._git,
            ignore_service=self._ignore,
        )
        self._metadata = InventoryMetadataService()
        self._default_large_file_review_bytes = default_large_file_review_bytes
        self._absolute_max_file_bytes = absolute_max_file_bytes
        self._max_directory_files = max_directory_files
        self._max_directory_bytes = max_directory_bytes
        self._max_directory_depth = max_directory_depth

    def build_candidate_set(self, project_root: Path) -> InventoryCandidateSet:
        root = project_root.resolve()
        catalog = self._loader.load_default()
        classifier = self._classifier(InventoryPolicyMatcher(catalog))
        source_mode: Literal[
            "git",
            "recursive",
            "fallback_after_git_error",
        ]
        if self._git.is_work_tree(root):
            try:
                candidates, summaries = self._enumeration.git_candidates(
                    root,
                    classifier=classifier,
                )
                source_mode = "git"
                warnings: tuple[str, ...] = (
                    ("tracked_missing_candidate_observed",)
                    if any(
                        item.base_outcome == InventoryCandidateOutcome.MISSING
                        for item in candidates
                    )
                    else ()
                )
            except (OSError, subprocess.SubprocessError):
                candidates, summaries = self._enumeration.recursive_candidates(
                    root,
                    classifier=classifier,
                )
                source_mode = "fallback_after_git_error"
                warnings = ("git_enumeration_failed_fallback_used",)
        else:
            candidates, summaries = self._enumeration.recursive_candidates(
                root,
                classifier=classifier,
            )
            source_mode = "recursive"
            warnings = ()
        digest = self._metadata.candidate_set_digest(
            source_mode=source_mode,
            candidates=candidates,
            summaries=summaries,
        )
        return InventoryCandidateSet(
            source_mode=source_mode,
            candidates=tuple(sorted(candidates, key=lambda item: item.path)),
            skipped_summaries=tuple(
                sorted(summaries, key=lambda item: item.path)
            ),
            warnings=warnings,
            inventory_policy_schema_version=catalog.schema_version,
            inventory_policy_digest=catalog.catalog_digest,
            filesystem_safety_version=FILESYSTEM_SAFETY_VERSION,
            candidate_set_digest=digest,
        )

    def resolve_requested_path(
        self,
        project_root: Path,
        path: str,
        *,
        candidate_set: InventoryCandidateSet,
    ) -> InventoryRequestedTargetResult:
        safe_path = self.normalize_requested_path(path)
        catalog = self._loader.load_default()
        if catalog.catalog_digest != candidate_set.inventory_policy_digest:
            raise InventorySelectionError(
                InventorySelectionErrorCode.PREFLIGHT_STALE,
                http_status=409,
                retryable=True,
            )
        classifier = self._classifier(InventoryPolicyMatcher(catalog))
        resolver = InventoryDirectoryResolver(
            classifier=classifier,
            inventory_policy_digest=catalog.catalog_digest,
            filesystem_safety_version=FILESYSTEM_SAFETY_VERSION,
            max_directory_files=self._max_directory_files,
            max_directory_bytes=self._max_directory_bytes,
            max_directory_depth=self._max_directory_depth,
            git_source_service=self._git,
            ignore_service=self._ignore,
            metadata_service=self._metadata,
        )
        return resolver.resolve(
            project_root.resolve(),
            safe_path,
            candidate_set=candidate_set,
        )

    def normalize_requested_path(self, path: str) -> str:
        if path == ".":
            return path
        if not path or any(character in path for character in "*?[]"):
            raise InventorySelectionError(
                InventorySelectionErrorCode.PATH_INVALID
            )
        try:
            return normalize_project_relative_path(path.rstrip("/"))
        except PathSafetyError as exc:
            raise InventorySelectionError(
                InventorySelectionErrorCode.PATH_INVALID
            ) from exc

    def _classifier(
        self,
        matcher: InventoryPolicyMatcher,
    ) -> InventoryCandidateClassifier:
        return InventoryCandidateClassifier(
            matcher=matcher,
            default_large_file_review_bytes=(
                self._default_large_file_review_bytes
            ),
            absolute_max_file_bytes=self._absolute_max_file_bytes,
            metadata_service=self._metadata,
        )
