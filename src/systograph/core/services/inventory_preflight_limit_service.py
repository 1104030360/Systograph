from __future__ import annotations

import stat
from pathlib import Path
from typing import Final

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryCandidateSet,
    InventoryDirectoryLimitKind,
    InventoryRequestedTargetResult,
)
from systograph.core.services.inventory_candidate_service import (
    MAX_RECURSIVE_DIRECTORY_BYTES,
    MAX_RECURSIVE_DIRECTORY_FILES,
)

MAX_REQUESTED_PATHS: Final = 100
MAX_DIRECTORY_SCOPES: Final = 20
MAX_REQUIRED_REVIEWS: Final = 200


class InventoryPreflightLimitService:
    def __init__(
        self,
        *,
        max_requested_paths: int = MAX_REQUESTED_PATHS,
        max_directory_scopes: int = MAX_DIRECTORY_SCOPES,
        max_aggregate_files: int = MAX_RECURSIVE_DIRECTORY_FILES,
        max_aggregate_bytes: int = MAX_RECURSIVE_DIRECTORY_BYTES,
        max_required_reviews: int = MAX_REQUIRED_REVIEWS,
    ) -> None:
        self._max_requested_paths = max_requested_paths
        self._max_directory_scopes = max_directory_scopes
        self._max_aggregate_files = max_aggregate_files
        self._max_aggregate_bytes = max_aggregate_bytes
        self._max_required_reviews = max_required_reviews

    def validate_path_count(self, paths: tuple[str, ...]) -> None:
        if len(paths) > self._max_requested_paths:
            raise InventorySelectionError(
                InventorySelectionErrorCode.PATH_INVALID,
                context={"limit": self._max_requested_paths},
            )

    def validate_directory_scope_count(
        self,
        project_root: Path,
        paths: tuple[str, ...],
    ) -> None:
        count = 0
        root = project_root.resolve()
        for path in paths:
            target = root if path == "." else root / path
            try:
                metadata = target.lstat()
            except OSError:
                continue
            if stat.S_ISDIR(metadata.st_mode):
                count += 1
        if count > self._max_directory_scopes:
            self._raise_limit(
                InventoryDirectoryLimitKind.DIRECTORY_SCOPE_COUNT,
                self._max_directory_scopes,
                count,
            )

    def validate_results(
        self,
        results: tuple[InventoryRequestedTargetResult, ...],
    ) -> None:
        unique: dict[str, InventoryCandidate] = {}
        for result in results:
            if result.directory_manifest is not None:
                unique.update(
                    {
                        item.path: item
                        for item in result.directory_manifest.entries
                    }
                )
        regular_count = sum(
            item.target_type == "regular_file" for item in unique.values()
        )
        if regular_count > self._max_aggregate_files:
            self._raise_limit(
                InventoryDirectoryLimitKind.AGGREGATE_OBSERVED_FILE_COUNT,
                self._max_aggregate_files,
                regular_count,
            )
        selectable_bytes = sum(
            item.size_bytes or 0
            for item in unique.values()
            if item.base_outcome
            in {
                InventoryCandidateOutcome.INCLUDED,
                InventoryCandidateOutcome.SOFT_EXCLUDED,
            }
        )
        if selectable_bytes > self._max_aggregate_bytes:
            self._raise_limit(
                InventoryDirectoryLimitKind.AGGREGATE_SELECTABLE_BYTES,
                self._max_aggregate_bytes,
                selectable_bytes,
            )

    def validate_required_reviews(
        self,
        candidate_set: InventoryCandidateSet,
    ) -> None:
        required_count = sum(
            item.decision_required for item in candidate_set.candidates
        )
        if required_count > self._max_required_reviews:
            raise InventorySelectionError(
                InventorySelectionErrorCode.REVIEW_LIMIT_EXCEEDED,
                context={
                    "limit": self._max_required_reviews,
                    "observed_at_least": required_count,
                },
            )

    def _raise_limit(
        self,
        kind: InventoryDirectoryLimitKind,
        limit: int,
        observed: int,
    ) -> None:
        raise InventorySelectionError(
            InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED,
            context={
                "limit_kind": kind.value,
                "limit": limit,
                "observed_at_least": observed,
            },
        )
