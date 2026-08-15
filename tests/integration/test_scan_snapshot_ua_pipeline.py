from __future__ import annotations

from pathlib import Path

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaAnalysisStats,
    UaCallRow,
    UaStructuralResult,
)
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.scan_snapshot_service import ScanSnapshotService
from systograph.core.services.ua_structural_adapter import UaStructuralAdapter


class CountingUaAnalysisService:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, FileInventory]] = []

    def analyze(
        self,
        project_root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisResult:
        self.calls.append((project_root, inventory))
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


def test_snapshot_runs_ua_once_and_persists_adapted_scan_result(
    tmp_path: Path,
) -> None:
    # Given: a final approved inventory and the active UA pipeline.
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("main()\n", encoding="utf-8")
    analyzer = CountingUaAnalysisService()
    repository = LocalJsonStateProvider(tmp_path / "state")
    service = ScanSnapshotService(
        project_scan_service=ProjectScanService(providers=[]),
        repository=repository,
        ua_analysis_service=analyzer,
        ua_adapter=UaStructuralAdapter(),
        scan_id_factory=iter(("scan:s1", "scan:s2")).__next__,
    )
    inventory = service.build_inventory(project_root)

    # When: initial scan and an explicit rescan each create a snapshot.
    first = service.scan_and_save(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    second = service.scan_and_save(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    # Then: UA runs once per scan, while each immutable snapshot is complete.
    assert len(analyzer.calls) == 2
    assert first.scan_id == "scan:s1"
    assert second.scan_id == "scan:s2"
    assert first.ua_analysis_result is not None
    assert first.ua_analysis_result.semantic is None
    assert [fact.provider for fact in first.scan_result.facts] == [
        "understand_anything"
    ]
    assert len(first.scan_result.evidence) == 1
    assert repository.get_snapshot("project:demo", "scan:s1") == first
