from __future__ import annotations

from pathlib import Path
from typing import Any

from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.services.path_safety_service import redact_local_paths
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)
from systograph.core.services.snapshot_safety_service import (
    SnapshotSafetyService,
)


class LocalJsonSnapshotSafety:
    def __init__(
        self,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()

    def sanitize(
        self,
        snapshot: ScanSnapshot,
        *,
        workspace_root: Path | None,
    ) -> ScanSnapshot:
        payload = self._sanitize_value(
            snapshot.model_dump(mode="json"),
            workspace_root=workspace_root,
        )
        safe = ScanSnapshot.model_validate(payload)
        SnapshotSafetyService(
            workspace_root=workspace_root
        ).assert_safe_json_like(
            safe.model_dump(mode="json"),
            source="snapshot.json",
        )
        return safe

    def _sanitize_value(
        self,
        value: Any,
        *,
        workspace_root: Path | None,
    ) -> Any:
        masked = self._masking_service.mask_json_like(value)
        if isinstance(masked, str):
            return redact_local_paths(masked, workspace_root=workspace_root)
        if isinstance(masked, dict):
            return {
                key: self._sanitize_value(child, workspace_root=workspace_root)
                for key, child in masked.items()
            }
        if isinstance(masked, list):
            return [
                self._sanitize_value(child, workspace_root=workspace_root)
                for child in masked
            ]
        return masked
