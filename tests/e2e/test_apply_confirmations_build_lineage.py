from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.manual_mapping_service import ManualMappingService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.web.app import LocalApiApp, create_app

SCOPED_JSON_ARTIFACTS = (
    "profile_signals.json",
    "readiness_report.json",
    "call_graph.json",
    "dataflow_hints.json",
    "execution_paths.json",
    "evidence_table.json",
)


class CountingProjectScanService(ProjectScanService):
    def __init__(self) -> None:
        super().__init__()
        self.inventory_calls = 0
        self.provider_calls = 0

    def build_inventory(self, project_root: Path) -> FileInventory:
        self.inventory_calls += 1
        return super().build_inventory(project_root)

    def scan_inventory(
        self,
        project_root: Path,
        *,
        inventory: FileInventory,
        inventory_policy: InventoryPolicyOverlay | None = None,
    ) -> ProjectScanResult:
        self.provider_calls += 1
        return super().scan_inventory(
            project_root,
            inventory=inventory,
            inventory_policy=inventory_policy,
        )


def counted_app(
    state_dir: Path,
    scanner: CountingProjectScanService,
) -> LocalApiApp:
    repository = LocalJsonStateProvider(state_dir)
    mappings = ManualMappingService(repository=repository)
    return create_app(
        state_dir=state_dir,
        manual_mapping_service=mappings,
        map_build_service=MapBuildService(
            project_scan_service=scanner,
            manual_mapping_service=mappings,
        ),
        scan_snapshot_service=ScanSnapshotService(
            project_scan_service=scanner,
            repository=repository,
        ),
    )


def import_project(client: TestClient, project_root: Path) -> str:
    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )
    assert response.status_code == 200
    return str(response.json()["project_id"])


def scan_project(
    client: TestClient,
    *,
    project_id: str,
    output_dir: Path,
) -> dict[str, object]:
    response = client.post(
        "/api/scans",
        json={"project_id": project_id, "output": str(output_dir)},
    )
    assert response.status_code == 200
    payload = cast(dict[str, object], response.json())
    assert payload["status"] == "completed"
    return payload


def create_mapping(
    client: TestClient,
    *,
    project_id: str,
    unmapped: dict[str, object],
    index: int,
) -> str:
    response = client.post(
        "/api/mappings",
        json={
            "project_id": project_id,
            "mapping_type": "existing_slot_mapping",
            "decision": "confirmed",
            "source_unmapped_id": unmapped["id"],
            "source_file": unmapped["source_file"],
            "observed_kind": unmapped["observed_kind"],
            "evidence_ids": unmapped["evidence_ids"],
            "target_slot": "vector_store",
            "component_name": f"Confirmed Vector Store {index}",
            "component_kind": "vector_db",
        },
    )
    assert response.status_code == 200
    return str(response.json()["mapping_id"])


def assert_build_artifacts(
    state_dir: Path,
    *,
    project_id: str,
    scan_id: str,
    build_id: str,
) -> None:
    repository = LocalJsonStateProvider(state_dir)
    manifest = repository.get_build_manifest(project_id, build_id)
    assert manifest is not None
    snapshot = repository.get_snapshot(project_id, scan_id)
    assert snapshot is not None
    assert snapshot.ua_analysis_result is None
    assert len(manifest.artifact_digests) == 10
    output_dir = Path(manifest.output_dir)
    for name in manifest.artifact_digests:
        assert (output_dir / name).is_file()
    for name in SCOPED_JSON_ARTIFACTS:
        payload = json.loads((output_dir / name).read_text(encoding="utf-8"))
        assert payload["build_id"] == build_id
        assert payload["scan_id"] == scan_id
        assert payload["generated_from_build_id"] == build_id
    evidence_table = json.loads(
        (output_dir / "evidence_table.json").read_text(encoding="utf-8")
    )
    assert any(
        row["review_state"] == "confirmed" for row in evidence_table["rows"]
    )

    loaded = BuildManifestService(repository=repository).load(manifest)
    assert loaded.normalized_ai_system_map is not None
    assert loaded.profile_inference_result is not None
    assert loaded.readiness_report is not None
    evidence_ids = {
        item.evidence_id for item in loaded.normalized_ai_system_map.evidence
    }
    assert all(
        set(item.evidence_ids) <= evidence_ids
        for item in loaded.profile_inference_result.profiles
    )
    assert all(
        set(item.evidence_ids) <= evidence_ids
        for item in loaded.readiness_report.findings
    )


def test_apply_lineage_restart_and_explicit_rescan(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "chromadb==0.5.0\nqdrant-client==1.12.1\n",
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "output"
    scanner = CountingProjectScanService()

    with TestClient(counted_app(state_dir, scanner)) as first:
        project_id = import_project(first, project_root)
        initial = scan_project(
            first,
            project_id=project_id,
            output_dir=output_dir,
        )
        build_result = initial["build_result"]
        assert isinstance(build_result, dict)
        lineage = build_result["lineage"]
        system_map = build_result["ai_system_map"]
        assert isinstance(lineage, dict)
        assert isinstance(system_map, dict)
        scan_id = str(initial["scan_id"])
        base_build_id = str(lineage["build_id"])
        unmapped = system_map["unmapped_components"]
        assert isinstance(unmapped, list)
        assert len(unmapped) >= 2
        mapping_ids = [
            create_mapping(
                first,
                project_id=project_id,
                unmapped=item,
                index=index,
            )
            for index, item in enumerate(unmapped[:2], start=1)
            if isinstance(item, dict)
        ]
        assert len(mapping_ids) == 2
        assert scanner.inventory_calls == scanner.provider_calls == 1

        applied_response = first.post(
            f"/api/map-builds/{base_build_id}/apply",
            json={"mapping_ids": mapping_ids},
        )
        assert applied_response.status_code == 200
        applied = applied_response.json()
        applied_build_id = str(applied["build_id"])
        assert applied["scan_id"] == scan_id
        assert applied["based_on_build_id"] == base_build_id
        assert applied["applied_mapping_ids"] == sorted(mapping_ids)
        assert scanner.inventory_calls == scanner.provider_calls == 1

    assert_build_artifacts(
        state_dir,
        project_id=project_id,
        scan_id=scan_id,
        build_id=applied_build_id,
    )

    with TestClient(counted_app(state_dir, scanner)) as restarted:
        assert restarted.get(f"/api/projects/{project_id}").status_code == 200
        mappings = restarted.get(
            f"/api/mappings?project_id={project_id}"
        ).json()["mappings"]
        assert {item["mapping_id"] for item in mappings} >= set(mapping_ids)
        assert (
            restarted.get(
                f"/api/projects/{project_id}/map-builds/latest"
            ).json()["build_id"]
            == applied_build_id
        )
        assert (
            restarted.get(f"/api/map-builds/{base_build_id}").status_code
            == 200
        )
        history = restarted.get(
            f"/api/projects/{project_id}/map-builds"
        ).json()["builds"]
        assert [item["build_id"] for item in history] == [
            base_build_id,
            applied_build_id,
        ]
        reused = restarted.post(
            "/api/projects/import",
            json={
                "source_type": "local_path",
                "project_path": str(project_root),
            },
        ).json()
        assert reused["project_id"] == project_id
        assert reused["reused"] is True
        assert scanner.inventory_calls == scanner.provider_calls == 1

        rescanned = scan_project(
            restarted,
            project_id=project_id,
            output_dir=output_dir,
        )
        rescan_result = rescanned["build_result"]
        assert isinstance(rescan_result, dict)
        rescan_lineage = rescan_result["lineage"]
        assert isinstance(rescan_lineage, dict)
        assert rescanned["scan_id"] != scan_id
        assert rescan_lineage["build_id"] != applied_build_id
        assert rescan_lineage["build_reason"] == "initial_scan"
        assert scanner.inventory_calls == scanner.provider_calls == 2
