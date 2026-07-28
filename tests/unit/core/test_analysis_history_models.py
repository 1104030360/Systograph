from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from systograph.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildLineage,
    ScanSnapshot,
    ScanSnapshotManifest,
)
from systograph.core.models.scan import ProjectScanResult


def test_apply_build_requires_parent_and_unique_mapping_ids() -> None:
    build = MapBuildLineage(
        project_id="project:demo",
        scan_id="scan:s1",
        build_id="build:b2",
        based_on_build_id="build:b1",
        build_reason="apply_confirmations",
        applied_mapping_ids=("mapping:m1",),
        generated_at=datetime(2026, 7, 4, 10, 30, tzinfo=UTC),
    )

    assert build.scan_id == "scan:s1"


@pytest.mark.parametrize(
    ("parent", "mapping_ids"),
    [
        (None, ("mapping:m1",)),
        ("build:b1", ()),
        ("build:b1", ("mapping:m1",) * 2),
    ],
)
def test_apply_build_rejects_invalid_lineage_shape(
    parent: str | None,
    mapping_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        MapBuildLineage(
            project_id="project:demo",
            scan_id="scan:s1",
            build_id="build:b2",
            based_on_build_id=parent,
            build_reason="apply_confirmations",
            applied_mapping_ids=mapping_ids,
            generated_at=datetime(2026, 7, 4, 10, 30, tzinfo=UTC),
        )


def test_initial_build_rejects_parent_build() -> None:
    with pytest.raises(ValidationError):
        MapBuildLineage(
            project_id="project:demo",
            scan_id="scan:s1",
            build_id="build:b1",
            based_on_build_id="build:older",
            build_reason="initial_scan",
            generated_at=datetime(2026, 7, 4, 10, 30, tzinfo=UTC),
        )


def test_scan_snapshot_identity_matches_scan_result_scope() -> None:
    snapshot = ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=datetime(2026, 7, 4, 10, 30, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(files_scanned=1),
    )

    assert snapshot.ua_analysis_result is None


def test_latest_pointer_revision_is_monotonic_positive() -> None:
    pointer = LatestBuildPointer(
        project_id="project:demo",
        latest_build_id="build:b1",
        revision=1,
        updated_at=datetime(2026, 7, 4, 10, 30, tzinfo=UTC),
    )

    assert pointer.revision == 1


def test_legacy_snapshot_models_mark_unknown_inventory_policy() -> None:
    snapshot = ScanSnapshot.model_validate(
        {
            "project_id": "project:demo",
            "scan_id": "scan:s1",
            "generated_at": "2026-07-04T10:30:00Z",
            "inventory_digest": "sha256:inventory",
            "scan_result": {"files_scanned": 1},
        }
    )
    manifest = ScanSnapshotManifest.model_validate(
        {
            "project_id": "project:demo",
            "scan_id": "scan:s1",
            "generated_at": "2026-07-04T10:30:00Z",
            "inventory_digest": "sha256:inventory",
        }
    )

    assert snapshot.inventory_provenance_status == (
        "legacy_inventory_policy_unknown"
    )
    assert manifest.inventory_provenance_status == (
        "legacy_inventory_policy_unknown"
    )
    assert snapshot.inventory_policy_digest is None
    assert manifest.inventory_run_digest is None
