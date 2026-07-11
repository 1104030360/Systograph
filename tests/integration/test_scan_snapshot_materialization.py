from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.scan import OutputRun, ProjectScanResult, ScanFact
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.models.template import RagTemplate
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService


class CountingScanService(ProjectScanService):
    def __init__(self) -> None:
        self.calls = 0

    def scan(
        self,
        project_root: Path,
        *,
        inventory_policy: InventoryPolicyOverlay | None = None,
    ) -> ProjectScanResult:
        self.calls += 1
        return ProjectScanResult(
            evidence=[
                Evidence(
                    id="evidence:retriever",
                    kind="code_pattern",
                    file="src/retriever.py",
                    path="Retriever.search",
                    line_start=1,
                    rule_id="retriever_rule",
                )
            ],
            files_scanned=1,
        )


class CountingComponentDetector(ComponentDetectionService):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def detect(
        self,
        *,
        template: RagTemplate,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
    ) -> ComponentDetectionResult:
        self.calls += 1
        return super().detect(
            template=template,
            facts=facts,
            evidence=evidence,
        )


def test_second_build_reuses_snapshot_without_filesystem_scan(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    scanner = CountingScanService()
    state = LocalJsonStateProvider(tmp_path / "state")
    snapshot = ScanSnapshotService(
        project_scan_service=scanner,
        repository=state,
    ).scan_and_save(
        project_id="project:demo",
        project_root=project_root,
    )
    detector = CountingComponentDetector()
    service = MapBuildService(
        project_scan_service=scanner,
        component_detection_service=detector,
    )
    request = MapBuildRequest(
        project_path=project_root,
        output=tmp_path / "output",
    )

    first = service.build_from_snapshot(
        snapshot,
        request=request,
        output_run=OutputRun(root_dir=tmp_path / "output" / "build_b1"),
        build_id="build:b1",
        build_reason="initial_scan",
    )
    second = service.build_from_snapshot(
        snapshot,
        request=request,
        output_run=OutputRun(root_dir=tmp_path / "output" / "build_b2"),
        build_id="build:b2",
        based_on_build_id="build:b1",
        build_reason="apply_confirmations",
        mapping_ids=("mapping:m1",),
    )

    assert scanner.calls == 1
    assert detector.calls == 2
    assert first.lineage is not None
    assert second.lineage is not None
    assert first.lineage.scan_id == second.lineage.scan_id == snapshot.scan_id
    assert first.lineage.build_id != second.lineage.build_id
    assert first.profile_inference_result is not (
        second.profile_inference_result
    )
    assert first.profile_inference_result is not None
    assert second.profile_inference_result is not None
    assert first.profile_inference_result.build_id == "build:b1"
    assert second.profile_inference_result.build_id == "build:b2"
    assert second.profile_signals_path is not None
    assert second.profile_signals_path.is_file()


def test_initial_and_apply_builds_accept_missing_ua_sidecar(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    scanner = CountingScanService()
    snapshot = ScanSnapshotService(
        project_scan_service=scanner,
        repository=LocalJsonStateProvider(tmp_path / "state"),
    ).scan_and_save(
        project_id="project:demo",
        project_root=project_root,
        ua_analysis_result=None,
    )
    service = MapBuildService(project_scan_service=scanner)
    request = MapBuildRequest(project_path=project_root)

    initial = service.build_from_snapshot(
        snapshot,
        request=request,
        output_run=OutputRun(root_dir=tmp_path / "b1"),
        build_id="build:b1",
        build_reason="initial_scan",
    )
    applied = service.build_from_snapshot(
        snapshot,
        request=request,
        output_run=OutputRun(root_dir=tmp_path / "b2"),
        build_id="build:b2",
        based_on_build_id="build:b1",
        build_reason="apply_confirmations",
        mapping_ids=("mapping:m1",),
    )

    assert snapshot.ua_analysis_result is None
    assert initial.status == applied.status == "ok"
    assert scanner.calls == 1
