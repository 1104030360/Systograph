from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from kai_mind.core.models.analysis_history import ScanSnapshot
from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
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
    ) -> None:
        self._scanner = project_scan_service or ProjectScanService()
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._scan_id_factory = scan_id_factory or (lambda: f"scan:{uuid4()}")

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
            file_fingerprints=self._file_fingerprints(
                project_root,
                inventory,
            ),
            ua_analysis_result=ua_analysis_result,
        )
        return self._repository.save_snapshot(snapshot)

    def build_inventory(self, project_root: Path) -> FileInventory:
        return self._scanner.build_inventory(project_root)

    @staticmethod
    def _file_fingerprints(
        project_root: Path,
        inventory: FileInventory | None,
    ) -> dict[str, str]:
        if inventory is None:
            return {}
        fingerprints: dict[str, str] = {}
        for record in inventory.files:
            path = project_root / record.path
            try:
                content = path.read_bytes()
            except OSError:
                continue
            fingerprints[record.path] = (
                "sha256:" + hashlib.sha256(content).hexdigest()
            )
        return fingerprints
