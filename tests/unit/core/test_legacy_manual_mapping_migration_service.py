from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from systograph.core.models.mapping import ManualMappingType
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.providers.local_json_state_storage import (
    LocalJsonStateStorage,
)
from systograph.core.services.legacy_manual_mapping_migration_service import (
    LEGACY_MAPPING_MIGRATION_VERSION,
    LegacyManualMappingMigrationService,
)


def fixed_clock() -> datetime:
    return datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def test_dry_run_reports_conversion_without_writing_state(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    path = write_legacy_mapping(state_root, complete_legacy_payload())
    original = path.read_bytes()

    report = LegacyManualMappingMigrationService(
        state_root,
        clock=fixed_clock,
    ).migrate(apply=False)

    assert report.status == "dry_run"
    assert report.scanned == 1
    assert report.converted == 1
    assert report.already_migrated == 0
    assert report.requires_manual_review == 0
    assert report.failed == 0
    assert report.items[0].input_digest.startswith("sha256:")
    assert report.items[0].output_digest is not None
    assert path.read_bytes() == original
    assert not (state_root / "migration-backups").exists()


def test_apply_converts_and_quarantines_edges_then_restart_is_idempotent(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    path = write_legacy_mapping(state_root, complete_legacy_payload())
    service = LegacyManualMappingMigrationService(
        state_root,
        clock=fixed_clock,
    )

    first = service.migrate(apply=True)
    converted_bytes = path.read_bytes()
    payload = json.loads(converted_bytes)
    second = service.migrate(apply=True)

    assert first.status == "complete"
    assert first.converted == 1
    assert payload["mapping_id"] == "mapping:legacy-router"
    assert payload["mapping_type"] == (
        ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE.value
    )
    assert payload["decision"] == "confirmed"
    assert payload["capability_candidate_id"] == "extension:query-router"
    assert payload["capability_candidate_name"] == "Query Router"
    assert payload["capability_candidate_kind"] == "routing"
    assert payload["created_at"] == "2026-07-01T00:00:00Z"
    assert payload["updated_at"] == "2026-07-17T12:00:00Z"
    audit = payload["audit_metadata"]
    assert audit["legacy_mapping_migration_version"] == (
        LEGACY_MAPPING_MIGRATION_VERSION
    )
    assert audit["legacy_payload_digest"].startswith("sha256:")
    assert audit["quarantine_ref"].startswith("quarantine:")
    assert "extension_edges" not in payload
    assert first.items[0].warnings == ["legacy_extension_edges_quarantined"]
    assert second.status == "complete"
    assert second.already_migrated == 1
    assert second.converted == 0
    assert path.read_bytes() == converted_bytes
    loaded = LocalJsonStateProvider(state_root).list_for_project(
        "project:demo"
    )
    assert [item.mapping_id for item in loaded] == ["mapping:legacy-router"]
    for protected in state_root.rglob("*.legacy.json"):
        assert stat.S_IMODE(protected.stat().st_mode) == 0o600


def test_incomplete_confirmed_row_requires_review_without_guessing(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    payload = complete_legacy_payload()
    payload["extension_kind"] = None
    payload["reason"] = "contains sk-test-1234567890"
    path = write_legacy_mapping(state_root, payload)
    original = path.read_bytes()

    report = LegacyManualMappingMigrationService(
        state_root,
        clock=fixed_clock,
    ).migrate(apply=True)

    serialized = report.model_dump_json()
    assert report.status == "requires_manual_review"
    assert report.requires_manual_review == 1
    assert report.converted == 0
    assert report.items[0].quarantine_ref is not None
    assert path.read_bytes() == original
    assert "sk-test-1234567890" not in serialized
    assert "contains" not in serialized


def test_nonconfirmed_complete_row_preserves_decision(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    payload = complete_legacy_payload()
    payload["decision"] = "rejected"
    path = write_legacy_mapping(state_root, payload)

    report = LegacyManualMappingMigrationService(
        state_root,
        clock=fixed_clock,
    ).migrate(apply=True)
    converted = json.loads(path.read_text(encoding="utf-8"))

    assert report.status == "complete"
    assert converted["decision"] == "rejected"
    assert converted["mapping_type"] == ("non_baseline_capability_candidate")


def test_apply_failure_keeps_original_file_and_reports_stable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    path = write_legacy_mapping(state_root, complete_legacy_payload())
    original = path.read_bytes()
    real_replace = os.replace

    def fail_mapping_replace(source: Path, target: Path) -> None:
        if Path(target) == path:
            raise OSError("simulated replace failure with sk-test-1234567890")
        real_replace(source, target)

    monkeypatch.setattr(
        "systograph.core.providers.local_json_state_storage.os.replace",
        fail_mapping_replace,
    )

    report = LegacyManualMappingMigrationService(
        state_root,
        clock=fixed_clock,
    ).migrate(apply=True)

    assert report.status == "partial_requires_retry"
    assert report.failed == 1
    assert report.items[0].error_code == "legacy_mapping_migration_failed"
    assert path.read_bytes() == original
    assert "sk-test-1234567890" not in report.model_dump_json()


def test_project_lock_blocks_concurrent_apply_without_writing(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    path = write_legacy_mapping(state_root, complete_legacy_payload())
    original = path.read_bytes()
    lock_owner = LocalJsonStateStorage(state_root, lock_timeout=1.0)

    with lock_owner.project_lock("project:demo"):
        report = LegacyManualMappingMigrationService(
            state_root,
            lock_timeout=0.01,
        ).migrate(apply=True)

    assert report.status == "partial_requires_retry"
    assert report.failed == 1
    assert path.read_bytes() == original


def test_backup_index_keeps_every_migrated_row(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    first = complete_legacy_payload()
    second = complete_legacy_payload()
    second["mapping_id"] = "mapping:legacy-reranker"
    second["extension_id"] = "extension:reranker"
    second["extension_name"] = "Reranker"
    second["extension_kind"] = "reranker"
    write_legacy_mapping(state_root, first)
    write_legacy_mapping(state_root, second)

    report = LegacyManualMappingMigrationService(
        state_root,
        clock=fixed_clock,
    ).migrate(apply=True)

    index_path = (
        state_root / "migration-backups" / "project_demo" / "index.json"
    )
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert report.converted == 2
    assert [entry["mapping_id"] for entry in index["entries"]] == [
        "mapping:legacy-reranker",
        "mapping:legacy-router",
    ]
    assert stat.S_IMODE(index_path.stat().st_mode) == 0o600


def write_legacy_mapping(
    state_root: Path,
    payload: dict[str, object],
) -> Path:
    path = (
        state_root
        / "projects"
        / "project_demo"
        / "mappings"
        / f"{str(payload['mapping_id']).replace(':', '_')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def complete_legacy_payload() -> dict[str, object]:
    return {
        "project_id": "project:demo",
        "mapping_id": "mapping:legacy-router",
        "mapping_digest": "sha256:legacy",
        "mapping_type": "new_extension_component",
        "decision": "confirmed",
        "source_unmapped_id": "unmapped:router",
        "source_file": "src/router.py",
        "observed_kind": "router_like_evidence",
        "evidence_ids": ["evidence:router"],
        "reason": "Confirmed by operator.",
        "extension_id": "extension:query-router",
        "extension_name": "Query Router",
        "extension_kind": "routing",
        "extension_edges": [
            {
                "from": "retriever",
                "to": "extension:query-router",
                "relationship": "routes_to",
            }
        ],
        "proposal_id": "proposal:router",
        "decision_source": "proposal_accept",
        "audit_metadata": {"actor": "operator"},
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
    }
