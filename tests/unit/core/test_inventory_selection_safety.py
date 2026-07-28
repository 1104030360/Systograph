from __future__ import annotations

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.inventory_selection import (
    InventoryPreflightRequest,
    InventorySelectionScope,
)
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryProposal,
)
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.inventory_candidate_service import (
    InventoryCandidateService,
)
from systograph.core.services.inventory_post_decision_safety_service import (
    InventoryPostDecisionSafetyResult,
    InventoryPostDecisionSafetyService,
)
from systograph.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from systograph.core.services.inventory_selection_materializer import (
    InventorySelectionMaterializer,
)
from systograph.core.services.inventory_selection_service import (
    InventorySelectionService,
)
from systograph.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)


def _decision(
    proposals: dict[str, ScanBoundaryProposal],
    path: str,
    action: ScanBoundaryDecisionAction,
) -> ScanBoundaryDecisionRequest:
    proposal = proposals[path]
    target = proposal.target
    context = proposal.selection_context
    assert context is not None
    return ScanBoundaryDecisionRequest(
        target_path=path,
        fingerprint=target.fingerprint,
        decision=action,
        selection_scope=context.selection_scope,
    )


def test_selection_applies_exact_over_directory_and_materializes_audit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / "ignored-dir").mkdir(parents=True)
    (root / ".gitignore").write_text(
        "ignored.py\nignored-dir/\n",
        encoding="utf-8",
    )
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (root / ".env").write_text("TOKEN=safe-fixture\n", encoding="utf-8")
    (root / "ignored.py").write_text("ignored\n", encoding="utf-8")
    (root / "ignored-dir" / "keep.py").write_text(
        "keep\n",
        encoding="utf-8",
    )
    (root / "ignored-dir" / "skip.py").write_text(
        "skip\n",
        encoding="utf-8",
    )
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(
            requested_paths=(
                "app.py",
                "ignored.py",
                "ignored-dir",
                "ignored-dir/skip.py",
            )
        ),
    )
    proposals = {
        item.target.path: item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
    }
    decisions = (
        _decision(
            proposals,
            ".env",
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
        _decision(
            proposals,
            "ignored.py",
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
        _decision(
            proposals,
            "ignored-dir",
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
        _decision(
            proposals,
            "ignored-dir/skip.py",
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
        ),
        _decision(
            proposals,
            "app.py",
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
        ),
    )

    result = InventorySelectionService(
        preflight_service=preflight_service
    ).select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=decisions,
    )

    assert result.pending_proposals == ()
    assert result.inventory is not None
    assert [item.path for item in result.inventory.files] == [
        ".env",
        ".gitignore",
        "ignored-dir/keep.py",
        "ignored.py",
    ]
    audit = {
        item.path: item for item in result.inventory.inventory_policy_audit
    }
    assert audit["ignored-dir/keep.py"].decision_target_path == "ignored-dir"
    assert audit["ignored-dir/keep.py"].decision_scope == (
        "recursive_directory"
    )
    assert audit["ignored-dir/skip.py"].decision_target_path == (
        "ignored-dir/skip.py"
    )
    assert audit["ignored-dir/skip.py"].effective_outcome == "skipped"
    assert result.summary.included_file_count == 4
    assert result.summary.directory_scope_results[0].included_file_count == 1


def test_selection_without_required_sensitive_decision_stays_pending(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".env").write_text("TOKEN=safe-fixture\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    preflight = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )

    result = InventorySelectionService().select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=preflight.preflight_request_id,
        decisions=(),
    )

    assert result.inventory is None
    assert [item.target.path for item in result.pending_proposals] == [".env"]


def test_selection_without_optional_decisions_matches_plan19_baseline(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / "node_modules").mkdir(parents=True)
    (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (root / "ignored.py").write_text("ignored\n", encoding="utf-8")
    (root / "node_modules" / "module.js").write_text(
        "module\n",
        encoding="utf-8",
    )
    baseline = FilesystemProvider().build_inventory(root)
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )

    selected = InventorySelectionService(
        preflight_service=preflight_service
    ).select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(),
    )

    assert selected.inventory is not None
    assert [item.path for item in selected.inventory.files] == [
        item.path for item in baseline.files
    ]
    assert [
        (item.path, item.reason) for item in selected.inventory.skipped
    ] == [(item.path, item.reason) for item in baseline.skipped]


def test_soft_resource_exclusion_audit_keeps_filesystem_safety_source(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "large.py").write_text("large\n", encoding="utf-8")
    preflight_service = InventoryPreflightService(
        candidate_service=InventoryCandidateService(
            default_large_file_review_bytes=1
        )
    )
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )

    result = InventorySelectionService(
        preflight_service=preflight_service
    ).select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(),
    )

    assert result.inventory is not None
    audit = result.inventory.inventory_policy_audit[0]
    assert audit.reason == "large_file_review"
    assert audit.source == "filesystem_safety"


def test_selection_rejects_duplicate_decisions(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text("app\n", encoding="utf-8")
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    proposal = ScanBoundaryReviewService().create_selection_proposals(state)[0]
    decision = ScanBoundaryDecisionRequest(
        target_path="app.py",
        fingerprint=proposal.target.fingerprint,
        decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
    )

    with pytest.raises(InventorySelectionError) as exc_info:
        InventorySelectionService().select(
            project_id="project:demo",
            project_root=root,
            preflight_request_id=state.preflight_request_id,
            decisions=(decision, decision),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.DUPLICATE_DECISION
    )


def test_exact_binary_scan_is_blocked_after_decision(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "blob.dat").write_bytes(b"prefix\x00binary")
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("blob.dat",)),
    )
    proposal = ScanBoundaryReviewService().create_selection_proposals(state)[0]
    decision = ScanBoundaryDecisionRequest(
        target_path="blob.dat",
        fingerprint=proposal.target.fingerprint,
        decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
    )

    with pytest.raises(InventorySelectionError) as exc_info:
        InventorySelectionService().select(
            project_id="project:demo",
            project_root=root,
            preflight_request_id=state.preflight_request_id,
            decisions=(decision,),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.POST_DECISION_BLOCKED
    )


def test_directory_scan_skips_only_post_decision_blocked_child(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    target = root / "ignored"
    target.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (target / "safe.py").write_text("safe\n", encoding="utf-8")
    (target / "blob.dat").write_bytes(b"prefix\x00binary")
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("ignored",)),
    )
    proposal = ScanBoundaryReviewService().create_selection_proposals(state)[0]
    decision = ScanBoundaryDecisionRequest(
        target_path="ignored",
        fingerprint=proposal.target.fingerprint,
        decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        selection_scope=InventorySelectionScope.RECURSIVE_DIRECTORY,
    )

    result = InventorySelectionService().select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(decision,),
    )

    assert result.inventory is not None
    assert [item.path for item in result.inventory.files] == [
        ".gitignore",
        "ignored/safe.py",
    ]
    directory_result = result.summary.directory_scope_results[0]
    assert directory_result.included_file_count == 1
    assert directory_result.post_decision_blocked_file_count == 1


def test_directory_skip_keeps_precontent_hard_block_authoritative(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    target = root / "ignored"
    target.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("outside\n", encoding="utf-8")
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (target / "safe.py").write_text("safe\n", encoding="utf-8")
    (target / "outside-link.py").symlink_to(outside)
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("ignored",)),
    )
    proposals = {
        item.target.path: item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
    }

    result = InventorySelectionService(
        preflight_service=preflight_service
    ).select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(
            _decision(
                proposals,
                "ignored",
                ScanBoundaryDecisionAction.SKIP_THIS_RUN,
            ),
        ),
    )

    assert result.inventory is not None
    audit = {
        item.path: item for item in result.inventory.inventory_policy_audit
    }
    assert audit["ignored/safe.py"].effective_outcome == "skipped"
    assert audit["ignored/outside-link.py"].effective_outcome == (
        "hard_blocked"
    )
    scope = result.summary.directory_scope_results[0]
    assert scope.hard_blocked_file_count == 1


def test_deepest_directory_decision_wins_over_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    nested = root / "src" / "generated"
    nested.mkdir(parents=True)
    (root / "src" / "app.py").write_text("app\n", encoding="utf-8")
    (nested / "output.py").write_text("output\n", encoding="utf-8")
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(
            requested_paths=("src", "src/generated"),
        ),
    )
    proposals = {
        item.target.path: item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
    }
    decisions = (
        _decision(
            proposals,
            "src",
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
        _decision(
            proposals,
            "src/generated",
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
        ),
    )

    result = InventorySelectionService(
        preflight_service=preflight_service
    ).select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=decisions,
    )

    assert result.inventory is not None
    assert [item.path for item in result.inventory.files] == ["src/app.py"]
    audit = {
        item.path: item for item in result.inventory.inventory_policy_audit
    }
    assert audit["src/generated/output.py"].decision_target_path == (
        "src/generated"
    )


def test_changed_directory_manifest_is_rejected_as_target_changed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    target = root / "ignored"
    target.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (target / "one.py").write_text("one\n", encoding="utf-8")
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("ignored",)),
    )
    proposal = ScanBoundaryReviewService().create_selection_proposals(state)[0]
    decision = ScanBoundaryDecisionRequest(
        target_path="ignored",
        fingerprint=proposal.target.fingerprint,
        decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        selection_scope=InventorySelectionScope.RECURSIVE_DIRECTORY,
    )
    (target / "two.py").write_text("two\n", encoding="utf-8")

    with pytest.raises(InventorySelectionError) as exc_info:
        InventorySelectionService(preflight_service=preflight_service).select(
            project_id="project:demo",
            project_root=root,
            preflight_request_id=state.preflight_request_id,
            decisions=(decision,),
        )

    assert exc_info.value.code == InventorySelectionErrorCode.TARGET_CHANGED


def test_conflicting_decisions_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text("app\n", encoding="utf-8")
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    proposal = ScanBoundaryReviewService().create_selection_proposals(state)[0]
    scan = ScanBoundaryDecisionRequest(
        target_path="app.py",
        fingerprint=proposal.target.fingerprint,
        decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
    )
    skip = scan.model_copy(
        update={"decision": ScanBoundaryDecisionAction.SKIP_THIS_RUN}
    )

    with pytest.raises(InventorySelectionError) as exc_info:
        InventorySelectionService().select(
            project_id="project:demo",
            project_root=root,
            preflight_request_id=state.preflight_request_id,
            decisions=(scan, skip),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.CONFLICTING_DECISION
    )


def test_hard_blocked_and_missing_targets_cannot_be_overridden(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    service = InventoryPreflightService()
    state = service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=(".git", "missing.py")),
    )

    for path, expected in (
        (".git", InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED),
        ("missing.py", InventorySelectionErrorCode.TARGET_MISSING),
    ):
        decision = ScanBoundaryDecisionRequest(
            target_path=path,
            fingerprint="sha256:forged",
            decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        )
        with pytest.raises(InventorySelectionError) as exc_info:
            InventorySelectionService(preflight_service=service).select(
                project_id="project:demo",
                project_root=root,
                preflight_request_id=state.preflight_request_id,
                decisions=(decision,),
            )
        assert exc_info.value.code == expected


def test_combined_directory_decisions_revalidate_aggregate_budget(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    for dirname in ("one", "two"):
        (root / dirname).mkdir(parents=True)
        (root / dirname / "file.py").write_text("x\n", encoding="utf-8")
    preflight_service = InventoryPreflightService(max_aggregate_files=1)
    states = [
        preflight_service.create(
            "project:demo",
            root,
            InventoryPreflightRequest(requested_paths=(dirname,)),
        )
        for dirname in ("one", "two")
    ]
    proposals = {
        item.target.path: item
        for state in states
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
        if item.target.target_type == "directory"
    }
    decisions = (
        _decision(
            proposals,
            "one",
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
        _decision(
            proposals,
            "two",
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
        ),
    )

    with pytest.raises(InventorySelectionError) as exc_info:
        InventorySelectionService(preflight_service=preflight_service).select(
            project_id="project:demo",
            project_root=root,
            preflight_request_id=states[0].preflight_request_id,
            decisions=decisions,
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED
    )
    assert exc_info.value.context == {
        "limit_kind": "aggregate_observed_file_count",
        "limit": 1,
        "observed_at_least": 2,
    }


def test_directory_with_only_binary_children_fails_closed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    target = root / "ignored"
    target.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (target / "blob.dat").write_bytes(b"prefix\x00binary")
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("ignored",)),
    )
    proposals = {
        item.target.path: item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
    }

    with pytest.raises(InventorySelectionError) as exc_info:
        InventorySelectionService(preflight_service=preflight_service).select(
            project_id="project:demo",
            project_root=root,
            preflight_request_id=state.preflight_request_id,
            decisions=(
                _decision(
                    proposals,
                    "ignored",
                    ScanBoundaryDecisionAction.SCAN_THIS_RUN,
                ),
            ),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.DIRECTORY_NO_SCANNABLE_FILES
    )


def test_skipped_candidate_is_never_opened_by_post_decision_safety(
    tmp_path: Path,
) -> None:
    class NeverOpenSafety(InventoryPostDecisionSafetyService):
        def check(
            self, project_root: Path, candidate: object
        ) -> InventoryPostDecisionSafetyResult:
            raise AssertionError(
                f"skipped candidate was opened: {project_root}:{candidate}"
            )

    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text("app\n", encoding="utf-8")
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    proposals = {
        item.target.path: item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
    }
    selection = InventorySelectionService(
        preflight_service=preflight_service,
        materializer=InventorySelectionMaterializer(
            safety_service=NeverOpenSafety()
        ),
    )

    result = selection.select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(
            _decision(
                proposals,
                "app.py",
                ScanBoundaryDecisionAction.SKIP_THIS_RUN,
            ),
        ),
    )

    assert result.inventory is not None
    assert result.inventory.files == []


def test_safe_open_fails_closed_without_nofollow_primitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text("app\n", encoding="utf-8")
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    candidate = state.requested_target_results[0].file_candidate
    assert candidate is not None
    monkeypatch.delattr(os, "O_NOFOLLOW", raising=False)

    result = InventoryPostDecisionSafetyService().check(root, candidate)

    assert result.allowed is False
    assert result.reason_code == "safe_open_unavailable"


def test_safe_open_detects_fstat_change_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text("app\n", encoding="utf-8")
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    candidate = state.requested_target_results[0].file_candidate
    assert candidate is not None
    real_fstat = os.fstat

    def changed_fstat(handle: int) -> SimpleNamespace:
        metadata = real_fstat(handle)
        return SimpleNamespace(
            st_mode=metadata.st_mode,
            st_size=metadata.st_size + 1,
            st_mtime_ns=metadata.st_mtime_ns,
            st_dev=metadata.st_dev,
            st_ino=metadata.st_ino,
        )

    monkeypatch.setattr(os, "fstat", changed_fstat)

    result = InventoryPostDecisionSafetyService().check(root, candidate)

    assert result.allowed is False
    assert result.changed is True
    assert result.reason_code == "target_changed"


def test_safe_open_hashes_content_on_the_validated_handle(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    content = b"validated content\n"
    (root / "app.py").write_bytes(content)
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    candidate = state.requested_target_results[0].file_candidate
    assert candidate is not None

    result = InventoryPostDecisionSafetyService().check(root, candidate)

    assert result.allowed is True
    assert result.content_fingerprint == (
        "sha256:" + hashlib.sha256(content).hexdigest()
    )


def test_selection_with_same_decision_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (root / "ignored.py").write_text("ignored\n", encoding="utf-8")
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("ignored.py",)),
    )
    proposals = {
        item.target.path: item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
    }
    decisions = (
        _decision(
            proposals,
            "ignored.py",
            ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
    )
    service = InventorySelectionService(preflight_service=preflight_service)

    first = service.select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=decisions,
    )
    second = service.select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=decisions,
    )

    assert first.inventory is not None
    assert second.inventory is not None
    assert first.inventory.model_dump(
        mode="json"
    ) == second.inventory.model_dump(mode="json")


def test_decision_digest_binds_exact_vs_directory_scope(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    target = root / "ignored"
    target.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (target / "file.py").write_text("file\n", encoding="utf-8")
    preflight_service = InventoryPreflightService()
    state = preflight_service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(
            requested_paths=("ignored", "ignored/file.py"),
        ),
    )
    proposals = {
        (item.target.path, item.selection_context.selection_scope): item
        for item in ScanBoundaryReviewService().create_selection_proposals(
            state
        )
        if item.selection_context is not None
    }
    exact_proposal = proposals[
        ("ignored/file.py", InventorySelectionScope.EXACT_FILE)
    ]
    directory_proposal = proposals[
        ("ignored", InventorySelectionScope.RECURSIVE_DIRECTORY)
    ]
    service = InventorySelectionService(preflight_service=preflight_service)

    exact = service.select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(
            ScanBoundaryDecisionRequest(
                target_path="ignored/file.py",
                fingerprint=exact_proposal.target.fingerprint,
                decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
            ),
        ),
    )
    directory = service.select(
        project_id="project:demo",
        project_root=root,
        preflight_request_id=state.preflight_request_id,
        decisions=(
            ScanBoundaryDecisionRequest(
                target_path="ignored",
                fingerprint=directory_proposal.target.fingerprint,
                decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
                selection_scope=InventorySelectionScope.RECURSIVE_DIRECTORY,
            ),
        ),
    )

    assert exact.inventory is not None
    assert directory.inventory is not None
    assert [item.path for item in exact.inventory.files] == [
        item.path for item in directory.inventory.files
    ]
    assert exact.inventory.boundary_decision_digest != (
        directory.inventory.boundary_decision_digest
    )
    assert exact.inventory.inventory_run_digest != (
        directory.inventory.inventory_run_digest
    )
