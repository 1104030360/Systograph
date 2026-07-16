from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from kai_mind.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryDirectorySummary,
)


class InventoryMetadataService:
    def file_fingerprint(
        self,
        *,
        path: str,
        target_type: str,
        size_bytes: int | None,
        mtime_ns: int | None,
    ) -> str:
        return self.digest(
            {
                "path": path,
                "target_type": target_type,
                "size_bytes": size_bytes,
                "mtime_ns": mtime_ns,
            }
        )

    def directory_manifest_fingerprint(
        self,
        *,
        directory_path: str,
        entries: Sequence[InventoryCandidate],
        inventory_policy_digest: str,
        filesystem_safety_version: str,
    ) -> str:
        return self.digest(
            {
                "directory_path": directory_path,
                "selection_scope": "recursive_directory",
                "entries": [
                    self._candidate_manifest_payload(entry)
                    for entry in sorted(entries, key=lambda item: item.path)
                ],
                "inventory_policy_digest": inventory_policy_digest,
                "filesystem_safety_version": filesystem_safety_version,
            }
        )

    def candidate_set_digest(
        self,
        *,
        source_mode: str,
        candidates: Sequence[InventoryCandidate],
        summaries: Sequence[InventoryDirectorySummary],
    ) -> str:
        return self.digest(
            {
                "source_mode": source_mode,
                "candidates": [
                    item.model_dump(mode="json")
                    for item in sorted(candidates, key=lambda item: item.path)
                ],
                "skipped_summaries": [
                    item.model_dump(mode="json")
                    for item in sorted(summaries, key=lambda item: item.path)
                ],
            }
        )

    def preflight_request_id(
        self,
        *,
        project_id: str,
        source_mode: str,
        candidate_set_digest: str,
        inventory_policy_digest: str,
        filesystem_safety_version: str,
    ) -> str:
        digest = self.digest(
            {
                "project_id": project_id,
                "source_mode": source_mode,
                "candidate_set_digest": candidate_set_digest,
                "inventory_policy_digest": inventory_policy_digest,
                "filesystem_safety_version": filesystem_safety_version,
            }
        )
        return "preflight:" + digest.removeprefix("sha256:")

    def digest(self, value: Any) -> str:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def _candidate_manifest_payload(
        self,
        candidate: InventoryCandidate,
    ) -> dict[str, object]:
        return {
            "path": candidate.path,
            "target_type": candidate.target_type,
            "size_bytes": candidate.size_bytes,
            "mtime_ns": candidate.mtime_ns,
            "base_outcome": candidate.base_outcome.value,
            "reason_code": candidate.reason_code,
            "exclusion_sources": sorted(
                source.value for source in candidate.exclusion_sources
            ),
            "matched_inventory_policy_ids": sorted(
                candidate.matched_inventory_policy_ids
            ),
            "effective_inventory_policy_id": (
                candidate.effective_inventory_policy_id
            ),
            "risk_type": candidate.risk_type,
            "decision_required": candidate.decision_required,
            "override_allowed": candidate.override_allowed,
        }
