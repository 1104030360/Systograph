from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.filesystem import FileInventory
from systograph.core.models.inventory_selection import (
    InventoryPreflightRequest,
)
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.scan import OutputRun, ProjectScanResult, ScanFact
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
)
from systograph.core.models.structural_fact import StructuralFact
from systograph.core.models.system_map import Evidence
from systograph.core.models.template import RagTemplate
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from systograph.core.services.inventory_selection_service import (
    InventorySelectionService,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from systograph.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from systograph.core.services.scan_snapshot_service import ScanSnapshotService


def selected_inventory(project_root: Path) -> FileInventory:
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        project_root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    proposal = next(
        item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
        if item.target.path == "app.py"
    )
    result = InventorySelectionService(
        preflight_service=preflight_service
    ).select(
        project_id="project:demo",
        project_root=project_root,
        preflight_request_id=state.preflight_request_id,
        decisions=(
            ScanBoundaryDecisionRequest(
                target_path="app.py",
                fingerprint=proposal.target.fingerprint,
                decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
            ),
        ),
    )
    assert result.inventory is not None
    return result.inventory


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
        structural_facts: Sequence[StructuralFact] = (),
    ) -> ComponentDetectionResult:
        self.calls += 1
        return super().detect(
            template=template,
            facts=facts,
            evidence=evidence,
            structural_facts=structural_facts,
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


def test_snapshot_and_manifest_preserve_inventory_policy_provenance(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    state_root = tmp_path / "state"
    state = LocalJsonStateProvider(state_root)
    scanner = ProjectScanService()
    service = ScanSnapshotService(
        project_scan_service=scanner,
        repository=state,
        scan_id_factory=lambda: "scan:s1",
    )
    inventory = service.build_inventory(project_root)

    snapshot = service.scan_and_save(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    manifest_path = (
        state_root
        / "projects"
        / "project_demo"
        / "scans"
        / "scan_s1"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert snapshot.inventory_provenance_status == "recorded"
    assert snapshot.inventory_policy_schema_version == (
        inventory.inventory_policy_schema_version
    )
    assert snapshot.inventory_policy_digest == (
        inventory.inventory_policy_digest
    )
    assert snapshot.candidate_set_digest == inventory.candidate_set_digest
    assert snapshot.filesystem_safety_version == (
        inventory.filesystem_safety_version
    )
    assert snapshot.boundary_decision_digest == (
        inventory.boundary_decision_digest
    )
    assert snapshot.final_inventory_digest == inventory.final_inventory_digest
    assert snapshot.inventory_run_digest == inventory.inventory_run_digest
    assert snapshot.inventory_source_mode == inventory.source
    assert manifest["inventory_provenance_status"] == "recorded"
    assert manifest["inventory_policy_digest"] == (
        inventory.inventory_policy_digest
    )
    assert manifest["candidate_set_digest"] == inventory.candidate_set_digest
    assert manifest["filesystem_safety_version"] == (
        inventory.filesystem_safety_version
    )
    assert manifest["boundary_decision_digest"] == (
        inventory.boundary_decision_digest
    )
    assert manifest["final_inventory_digest"] == (
        inventory.final_inventory_digest
    )
    assert manifest["inventory_run_digest"] == inventory.inventory_run_digest


def test_snapshot_reuses_safe_fingerprint_without_path_read_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    app_path = project_root / "app.py"
    app_path.write_text("app\n", encoding="utf-8")
    inventory = selected_inventory(project_root)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path == app_path:
            raise AssertionError("snapshot used an unsafe path read")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    snapshot = ScanSnapshotService(
        project_scan_service=ProjectScanService(providers=[]),
        repository=LocalJsonStateProvider(tmp_path / "state"),
    ).scan_and_save(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert snapshot.file_fingerprints["app.py"].startswith("sha256:")


def test_snapshot_rejects_content_changed_after_selection(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    app_path = project_root / "app.py"
    app_path.write_text("one\n", encoding="utf-8")
    inventory = selected_inventory(project_root)
    app_path.write_text("changed\n", encoding="utf-8")
    repository = LocalJsonStateProvider(tmp_path / "state")

    with pytest.raises(InventorySelectionError) as exc_info:
        ScanSnapshotService(
            project_scan_service=ProjectScanService(providers=[]),
            repository=repository,
        ).scan_and_save(
            project_id="project:demo",
            project_root=project_root,
            inventory=inventory,
        )

    assert exc_info.value.code == InventorySelectionErrorCode.TARGET_CHANGED
    assert repository.get_snapshot("project:demo", "scan:missing") is None
