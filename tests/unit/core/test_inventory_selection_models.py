from __future__ import annotations

from typing import TypedDict

import pytest
from pydantic import ValidationError

from kai_mind.core.models.inventory_selection import (
    DirectorySelectionManifest,
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventorySelectionScope,
    InventorySelectionSource,
)
from kai_mind.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryProposal,
)
from kai_mind.core.services.inventory_metadata_service import (
    InventoryMetadataService,
)


def candidate(
    *,
    path: str = "src/app.py",
    size_bytes: int = 12,
    mtime_ns: int = 100,
) -> InventoryCandidate:
    return InventoryCandidate(
        path=path,
        target_type="regular_file",
        size_bytes=size_bytes,
        mtime_ns=mtime_ns,
        base_outcome=InventoryCandidateOutcome.INCLUDED,
        exclusion_sources=(),
        matched_inventory_policy_ids=(),
        reason_code="included_by_default",
        decision_required=False,
        override_allowed=True,
        metadata_fingerprint=InventoryMetadataService().file_fingerprint(
            path=path,
            target_type="regular_file",
            size_bytes=size_bytes,
            mtime_ns=mtime_ns,
        ),
    )


class FingerprintInput(TypedDict):
    path: str
    target_type: str
    size_bytes: int
    mtime_ns: int


@pytest.mark.parametrize(
    "changed",
    [
        {
            "path": "src/other.py",
            "target_type": "regular_file",
            "size_bytes": 12,
            "mtime_ns": 100,
        },
        {
            "path": "src/app.py",
            "target_type": "symlink",
            "size_bytes": 12,
            "mtime_ns": 100,
        },
        {
            "path": "src/app.py",
            "target_type": "regular_file",
            "size_bytes": 13,
            "mtime_ns": 100,
        },
        {
            "path": "src/app.py",
            "target_type": "regular_file",
            "size_bytes": 12,
            "mtime_ns": 101,
        },
    ],
)
def test_file_metadata_fingerprint_changes_for_every_bound_field(
    changed: FingerprintInput,
) -> None:
    service = InventoryMetadataService()
    baseline: FingerprintInput = {
        "path": "src/app.py",
        "target_type": "regular_file",
        "size_bytes": 12,
        "mtime_ns": 100,
    }

    first = service.file_fingerprint(**baseline)
    second = service.file_fingerprint(**changed)

    assert first.startswith("sha256:")
    assert first != second


def test_directory_manifest_fingerprint_is_sorted_and_content_free() -> None:
    service = InventoryMetadataService()
    first_entries = (
        candidate(path="src/b.py", size_bytes=5, mtime_ns=2),
        candidate(path="src/a.py", size_bytes=4, mtime_ns=1),
    )
    second_entries = tuple(reversed(first_entries))

    first = service.directory_manifest_fingerprint(
        directory_path="src",
        entries=first_entries,
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v1",
    )
    second = service.directory_manifest_fingerprint(
        directory_path="src",
        entries=second_entries,
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v1",
    )

    assert first == second
    assert "src" not in first
    assert "/Users/" not in first


@pytest.mark.parametrize(
    "update",
    [
        {"path": "src/renamed.py"},
        {"target_type": "symlink"},
        {"size_bytes": 6},
        {"mtime_ns": 3},
        {"base_outcome": InventoryCandidateOutcome.SOFT_EXCLUDED},
        {"reason_code": "gitignored"},
        {"exclusion_sources": (InventorySelectionSource.PROJECT_IGNORE,)},
        {"matched_inventory_policy_ids": ("inventory:rule",)},
        {"effective_inventory_policy_id": "inventory:rule"},
        {"risk_type": "secret_like_config"},
        {"decision_required": True},
        {"override_allowed": False},
    ],
)
def test_directory_manifest_fingerprint_binds_every_candidate_field(
    update: dict[str, object],
) -> None:
    service = InventoryMetadataService()
    entry = candidate(path="src/app.py", size_bytes=5, mtime_ns=2)
    baseline = service.directory_manifest_fingerprint(
        directory_path="src",
        entries=(entry,),
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v1",
    )

    changed = service.directory_manifest_fingerprint(
        directory_path="src",
        entries=(entry.model_copy(update=update),),
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v1",
    )

    assert changed != baseline


def test_directory_manifest_fingerprint_binds_scope_policy_and_safety() -> (
    None
):
    service = InventoryMetadataService()
    entry = candidate()
    baseline = service.directory_manifest_fingerprint(
        directory_path="src",
        entries=(entry,),
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v1",
    )

    assert baseline != service.directory_manifest_fingerprint(
        directory_path="other",
        entries=(entry,),
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v1",
    )
    assert baseline != service.directory_manifest_fingerprint(
        directory_path="src",
        entries=(entry,),
        inventory_policy_digest="sha256:changed",
        filesystem_safety_version="inventory-safety/v1",
    )
    assert baseline != service.directory_manifest_fingerprint(
        directory_path="src",
        entries=(entry,),
        inventory_policy_digest="sha256:policy",
        filesystem_safety_version="inventory-safety/v2",
    )


def test_inventory_selection_models_are_frozen_and_reject_unknown_fields() -> (
    None
):
    entry = candidate()
    manifest = DirectorySelectionManifest.from_entries(
        directory_path="src",
        entries=(entry,),
        manifest_fingerprint="sha256:manifest",
    )

    assert manifest.selection_scope == (
        InventorySelectionScope.RECURSIVE_DIRECTORY
    )
    assert manifest.observed_regular_file_count == 1
    with pytest.raises(ValidationError):
        InventoryCandidate.model_validate(
            {**entry.model_dump(), "unexpected": True}
        )
    with pytest.raises(ValidationError):
        entry.path = "changed.py"


def test_boundary_models_keep_legacy_shape_and_default_exact_scope() -> None:
    proposal = ScanBoundaryProposal.model_validate(
        {
            "proposal_id": "proposal:p1",
            "project_id": "project:demo",
            "status": "pending_user_confirmation",
            "target": {
                "path": ".env",
                "risk_type": "secret_like_config",
                "reason": "Review this path.",
                "fingerprint": "sha256:metadata",
            },
            "evidence_packet": {
                "project_id": "project:demo",
                "target_path": ".env",
                "risk_type": "secret_like_config",
                "reason": "Review this path.",
            },
            "created_at": "2026-07-16T00:00:00Z",
            "updated_at": "2026-07-16T00:00:00Z",
        }
    )
    decision = ScanBoundaryDecisionRequest(
        target_path=".env",
        fingerprint="sha256:metadata",
        decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
    )

    assert proposal.selection_context is None
    assert decision.selection_scope == InventorySelectionScope.EXACT_FILE


def test_candidate_exclusion_sources_are_typed() -> None:
    excluded = candidate().model_copy(
        update={
            "base_outcome": InventoryCandidateOutcome.SOFT_EXCLUDED,
            "exclusion_sources": (
                InventorySelectionSource.KAI_INVENTORY_CATALOG,
            ),
        }
    )

    assert excluded.exclusion_sources == (
        InventorySelectionSource.KAI_INVENTORY_CATALOG,
    )
