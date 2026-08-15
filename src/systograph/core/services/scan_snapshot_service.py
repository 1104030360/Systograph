from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import ProjectScanResult, ProviderScanResult
from systograph.core.models.ua_analysis import UaAnalysisResult
from systograph.core.models.ua_parity import UaParityReport
from systograph.core.services.inventory_post_decision_safety_service import (
    InventoryPostDecisionSafetyService,
)
from systograph.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from systograph.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)

Clock = Callable[[], datetime]
ScanIdFactory = Callable[[], str]


class SnapshotWriter(Protocol):
    def save_snapshot(self, snapshot: ScanSnapshot) -> ScanSnapshot: ...


class UaAnalysisService(Protocol):
    def analyze(
        self,
        project_root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisResult: ...


class UaResultAdapter(Protocol):
    def adapt(self, analysis: UaAnalysisResult) -> ProviderScanResult: ...


class UaParityReporter(Protocol):
    def compare_existing(
        self,
        *,
        inventory: FileInventory,
        legacy_scan: ProjectScanResult,
        ua_scan: ProviderScanResult,
    ) -> UaParityReport: ...


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
        ua_analysis_service: UaAnalysisService | None = None,
        ua_adapter: UaResultAdapter | None = None,
        ua_parity_service: UaParityReporter | None = None,
    ) -> None:
        self._scanner = project_scan_service or ProjectScanService()
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._scan_id_factory = scan_id_factory or (lambda: f"scan:{uuid4()}")
        self._content_safety = (
            content_safety_service or InventoryPostDecisionSafetyService()
        )
        if (ua_analysis_service is None) != (ua_adapter is None):
            raise ValueError("UA analysis service and adapter must be paired")
        if ua_parity_service is not None and ua_analysis_service is None:
            raise ValueError("UA parity requires the UA analysis pipeline")
        self._ua_analysis = ua_analysis_service
        self._ua_adapter = ua_adapter
        self._ua_parity = ua_parity_service

    def scan_and_save(
        self,
        *,
        project_id: str,
        project_root: Path,
        inventory_policy: InventoryPolicyOverlay | None = None,
        ua_analysis_result: UaAnalysisResult | None = None,
        inventory: FileInventory | None = None,
    ) -> ScanSnapshot:
        if self._ua_analysis is not None and inventory is None:
            inventory = self._scanner.build_inventory(project_root)
        file_fingerprints = self._file_fingerprints(project_root, inventory)
        scan_result = (
            self._scanner.scan(project_root, inventory_policy=inventory_policy)
            if inventory is None
            else self._scanner.scan_inventory(
                project_root,
                inventory=inventory,
                inventory_policy=inventory_policy,
            )
        )
        ua_parity_report: UaParityReport | None = None
        if self._ua_analysis is not None:
            if ua_analysis_result is not None:
                raise ValueError("UA analysis result cannot be injected")
            if inventory is None or self._ua_adapter is None:
                raise ValueError("UA analysis requires an approved inventory")
            ua_analysis_result = self._ua_analysis.analyze(
                project_root,
                inventory,
            )
            ua_scan = self._ua_adapter.adapt(ua_analysis_result)
            if self._ua_parity is not None:
                ua_parity_report = self._ua_parity.compare_existing(
                    inventory=inventory,
                    legacy_scan=scan_result.model_copy(deep=True),
                    ua_scan=ua_scan.model_copy(deep=True),
                )
            self._scanner.merge_provider_result(
                scan_result,
                ua_scan,
                "understand_anything",
            )
            if self._file_fingerprints(project_root, inventory) != (
                file_fingerprints
            ):
                raise InventorySelectionError(
                    InventorySelectionErrorCode.TARGET_CHANGED,
                    http_status=409,
                    retryable=True,
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
            file_fingerprints=file_fingerprints,
            inventory_selection_summary=(
                scan_result.inventory_selection_summary
            ),
            ua_analysis_result=ua_analysis_result,
            ua_parity_report=ua_parity_report,
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
