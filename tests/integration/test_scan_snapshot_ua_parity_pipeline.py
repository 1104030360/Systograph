from __future__ import annotations

from pathlib import Path

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import ProjectScanResult, ProviderScanResult
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaAnalysisStats,
    UaCallRow,
    UaStructuralResult,
)
from systograph.core.models.ua_parity import (
    UaParityInvocationCounters,
    UaParityReport,
    UaParitySummary,
)
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.scan_snapshot_service import ScanSnapshotService
from systograph.core.services.ua_structural_adapter import UaStructuralAdapter


class CountingUaAnalysisService:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(
        self,
        project_root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisResult:
        self.calls += 1
        return UaAnalysisResult(
            schema_version="systograph-ua-result/v1",
            status="completed",
            structural=UaStructuralResult(
                imports=(),
                symbols=(),
                calls=(
                    UaCallRow(
                        file="app.py",
                        caller="main",
                        callee="QdrantClient",
                        line_number=1,
                    ),
                ),
                resources=(),
                endpoints=(),
            ),
            semantic=None,
            warnings=(),
            stats=UaAnalysisStats(
                filesScanned=1,
                filesWithImports=0,
                totalEdges=0,
                totalBatches=1,
                algorithm="count-fallback",
                filesAnalyzed=1,
                batchCompletion=(),
            ),
            extra={},
        )


class RecordingParityService:
    def __init__(self) -> None:
        self.calls: list[
            tuple[FileInventory, ProjectScanResult, ProviderScanResult]
        ] = []

    def compare_existing(
        self,
        *,
        inventory: FileInventory,
        legacy_scan: ProjectScanResult,
        ua_scan: ProviderScanResult,
    ) -> UaParityReport:
        self.calls.append((inventory, legacy_scan, ua_scan))
        return UaParityReport(
            schema_version="systograph-ua-parity/v1",
            llm_mode="disabled",
            inventory_digest=(
                inventory.final_inventory_digest or "sha256:" + "0" * 64
            ),
            invocations=UaParityInvocationCounters(
                filesystem_scan=1,
                ua_sidecar=1,
                parity_providers=1,
            ),
            summary=UaParitySummary(
                equivalent=0,
                missing=0,
                extra=0,
                intentionally_degraded=0,
            ),
            comparisons=(),
        )


def test_snapshot_persists_one_pass_parity_report_for_apply_reuse(
    tmp_path: Path,
) -> None:
    # Given: one approved inventory and separately observable UA/parity stages.
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("main()\n", encoding="utf-8")
    analyzer = CountingUaAnalysisService()
    parity = RecordingParityService()
    repository = LocalJsonStateProvider(tmp_path / "state")
    service = ScanSnapshotService(
        project_scan_service=ProjectScanService(providers=[]),
        repository=repository,
        ua_analysis_service=analyzer,
        ua_adapter=UaStructuralAdapter(),
        ua_parity_service=parity,
        scan_id_factory=lambda: "scan:b1",
    )
    inventory = service.build_inventory(project_root)

    # When: B1 performs the only filesystem/provider/UA analysis pass.
    snapshot = service.scan_and_save(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    # Then: parity consumed existing results and is frozen into the snapshot.
    assert analyzer.calls == 1
    assert len(parity.calls) == 1
    _, legacy_scan, ua_scan = parity.calls[0]
    assert legacy_scan.facts == []
    assert {fact.provider for fact in ua_scan.facts} == {"understand_anything"}
    assert snapshot.ua_parity_report is not None
    assert snapshot.ua_parity_report.invocations == UaParityInvocationCounters(
        filesystem_scan=1,
        ua_sidecar=1,
        parity_providers=1,
    )
    assert repository.get_snapshot("project:demo", "scan:b1") == snapshot
