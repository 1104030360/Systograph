from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from kai_mind.core.models.analysis_history import ScanSnapshot
from kai_mind.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.services.inventory_post_decision_safety_service import (
    InventoryPostDecisionSafetyService,
)
from kai_mind.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from kai_mind.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)

Clock = Callable[[], datetime]
ScanIdFactory = Callable[[], str]


class SnapshotWriter(Protocol):
    def save_snapshot(self, snapshot: ScanSnapshot) -> ScanSnapshot: ...


class ScanSnapshotService:
    def __init__(
        self,
        *,
        project_scan_service: ProjectScanService | None = None,
        repository: SnapshotWriter,
        clock: Clock | None = None,
        scan_id_factory: ScanIdFactory | None = None,
        content_safety_service: InventoryPostDecisionSafetyService
        | None = None,
    ) -> None:
        self._scanner = project_scan_service or ProjectScanService()
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._scan_id_factory = scan_id_factory or (lambda: f"scan:{uuid4()}")
        self._content_safety = (
            content_safety_service or InventoryPostDecisionSafetyService()
        )

    def scan_and_save(
        self,
        *,
        project_id: str,
        project_root: Path,
        inventory_policy: InventoryPolicyOverlay | None = None,
        ua_analysis_result: dict[str, Any] | None = None,
        inventory: FileInventory | None = None,
    ) -> ScanSnapshot:
        scan_result = (
            self._scanner.scan(project_root, inventory_policy=inventory_policy)
            if inventory is None
            else self._scanner.scan_inventory(
                project_root,
                inventory=inventory,
                inventory_policy=inventory_policy,
            )
        )
        payload = scan_result.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        snapshot = ScanSnapshot(
            project_id=project_id,
            scan_id=self._scan_id_factory(),
            generated_at=self._clock(),
            inventory_digest=f"sha256:{digest}",
            scan_result=scan_result,
            inventory_provenance_status=(
                "recorded"
                if all(
                    (
                        scan_result.inventory_policy_schema_version,
                        scan_result.inventory_policy_digest,
                        scan_result.inventory_run_digest,
                        scan_result.inventory_source_mode,
                    )
                )
                else "legacy_inventory_policy_unknown"
            ),
            inventory_policy_schema_version=(
                scan_result.inventory_policy_schema_version
            ),
            inventory_policy_digest=scan_result.inventory_policy_digest,
            candidate_set_digest=scan_result.candidate_set_digest,
            filesystem_safety_version=scan_result.filesystem_safety_version,
            boundary_decision_digest=scan_result.boundary_decision_digest,
            final_inventory_digest=scan_result.final_inventory_digest,
            inventory_run_digest=scan_result.inventory_run_digest,
            inventory_source_mode=scan_result.inventory_source_mode,
            file_fingerprints=self._file_fingerprints(
                project_root,
                inventory,
            ),
            inventory_selection_summary=(
                scan_result.inventory_selection_summary
            ),
            ua_analysis_result=ua_analysis_result,
        )
        return self._repository.save_snapshot(snapshot)

    def build_inventory(self, project_root: Path) -> FileInventory:
        return self._scanner.build_inventory(project_root)

    @property
    def inventory_rule_loader(self) -> ScanInventoryRuleLoader | None:
        return self._scanner.inventory_rule_loader

    def _file_fingerprints(
        self,
        project_root: Path,
        inventory: FileInventory | None,
    ) -> dict[str, str]:
        if inventory is None:
            return {}
        fingerprints: dict[str, str] = {}
        for record in inventory.files:
            result = self._content_safety.fingerprint_record(
                project_root,
                path=record.path,
                expected_size_bytes=record.size_bytes,
                expected_metadata_fingerprint=record.metadata_fingerprint,
            )
            if not result.allowed or result.content_fingerprint is None:
                raise InventorySelectionError(
                    (
                        InventorySelectionErrorCode.TARGET_CHANGED
                        if result.changed
                        else InventorySelectionErrorCode.POST_DECISION_BLOCKED
                    ),
                    http_status=409 if result.changed else 422,
                    retryable=result.changed,
                )
            if (
                record.content_fingerprint is not None
                and record.content_fingerprint != result.content_fingerprint
            ):
                raise InventorySelectionError(
                    InventorySelectionErrorCode.TARGET_CHANGED,
                    http_status=409,
                    retryable=True,
                )
            fingerprints[record.path] = result.content_fingerprint
        return fingerprints
