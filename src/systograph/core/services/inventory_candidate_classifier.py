from __future__ import annotations

import stat
from os import stat_result
from typing import Final

from systograph.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventorySelectionSource,
)
from systograph.core.services.inventory_metadata_service import (
    InventoryMetadataService,
)
from systograph.core.services.inventory_policy_matcher import (
    InventoryPolicyMatcher,
)
from systograph.core.services.inventory_risk_service import (
    InventoryRiskService,
)

DEFAULT_LARGE_FILE_REVIEW_BYTES: Final = 1_000_000
DEFAULT_ABSOLUTE_MAX_FILE_BYTES: Final = 100_000_000


class InventoryCandidateClassifier:
    def __init__(
        self,
        *,
        matcher: InventoryPolicyMatcher,
        default_large_file_review_bytes: int = (
            DEFAULT_LARGE_FILE_REVIEW_BYTES
        ),
        absolute_max_file_bytes: int = DEFAULT_ABSOLUTE_MAX_FILE_BYTES,
        metadata_service: InventoryMetadataService | None = None,
        risk_service: InventoryRiskService | None = None,
    ) -> None:
        self.matcher = matcher
        self._default_large_file_review_bytes = default_large_file_review_bytes
        self._absolute_max_file_bytes = absolute_max_file_bytes
        self._metadata_service = metadata_service or InventoryMetadataService()
        self._risk_service = risk_service or InventoryRiskService()

    def classify(
        self,
        path: str,
        metadata: stat_result | None,
        *,
        exclusion_source: InventorySelectionSource | None = None,
    ) -> InventoryCandidate:
        target_type = self._target_type(metadata)
        size_bytes = metadata.st_size if metadata is not None else None
        mtime_ns = metadata.st_mtime_ns if metadata is not None else None
        fingerprint = self._metadata_service.file_fingerprint(
            path=path,
            target_type=target_type,
            size_bytes=size_bytes,
            mtime_ns=mtime_ns,
        )
        hard_reason = self._hard_reason(path, metadata)
        if hard_reason is not None:
            return InventoryCandidate(
                path=path,
                target_type=target_type,
                size_bytes=size_bytes,
                mtime_ns=mtime_ns,
                base_outcome=(
                    InventoryCandidateOutcome.MISSING
                    if metadata is None
                    else InventoryCandidateOutcome.HARD_BLOCKED
                ),
                exclusion_sources=(
                    InventorySelectionSource.FILESYSTEM_SAFETY,
                ),
                matched_inventory_policy_ids=(),
                reason_code=hard_reason,
                decision_required=False,
                override_allowed=False,
                metadata_fingerprint=fingerprint,
            )

        policy_match = self.matcher.match(path)
        sources: list[InventorySelectionSource] = []
        reason = "included_by_default"
        if exclusion_source is not None:
            sources.append(exclusion_source)
            reason = "gitignored"
        if policy_match.effective_action is not None and (
            policy_match.effective_action.value == "exclude"
        ):
            sources.append(
                InventorySelectionSource.SYSTOGRAPH_INVENTORY_CATALOG
            )
            reason = policy_match.effective_reason or "catalog_excluded"
        if (
            size_bytes is not None
            and size_bytes > self._default_large_file_review_bytes
        ):
            sources.append(InventorySelectionSource.FILESYSTEM_SAFETY)
            reason = "large_file_review"
        outcome = (
            InventoryCandidateOutcome.SOFT_EXCLUDED
            if sources
            else InventoryCandidateOutcome.INCLUDED
        )
        risk_type = self._risk_service.risk_type(path)
        return InventoryCandidate(
            path=path,
            target_type=target_type,
            size_bytes=size_bytes,
            mtime_ns=mtime_ns,
            base_outcome=outcome,
            exclusion_sources=tuple(dict.fromkeys(sources)),
            matched_inventory_policy_ids=(
                policy_match.matched_inventory_policy_ids
            ),
            effective_inventory_policy_id=(
                policy_match.effective_inventory_policy_id
            ),
            reason_code=reason,
            risk_type=risk_type,
            decision_required=(
                risk_type is not None
                and outcome == InventoryCandidateOutcome.INCLUDED
            ),
            override_allowed=True,
            metadata_fingerprint=fingerprint,
        )

    def _hard_reason(
        self,
        path: str,
        metadata: stat_result | None,
    ) -> str | None:
        if metadata is None:
            return "missing_at_scan"
        if path == ".git" or path.startswith(".git/"):
            return "git_directory"
        if stat.S_ISLNK(metadata.st_mode):
            return "symlink_not_allowed"
        if not stat.S_ISREG(metadata.st_mode):
            return "unsupported_file_type"
        if metadata.st_size > self._absolute_max_file_bytes:
            return "absolute_size_cap"
        return None

    def _target_type(self, metadata: stat_result | None) -> str:
        if metadata is None:
            return "missing"
        if stat.S_ISREG(metadata.st_mode):
            return "regular_file"
        if stat.S_ISDIR(metadata.st_mode):
            return "directory"
        if stat.S_ISLNK(metadata.st_mode):
            return "symlink"
        return "special"
