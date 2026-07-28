from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import IO, Any, cast

import pytest

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.inventory_selection import (
    InventoryPreflightRequest,
)
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
)
from systograph.core.services.inventory_candidate_service import (
    InventoryCandidateService,
)
from systograph.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from systograph.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / ".gitignore").write_text(
        "ignored-*.py\nnode_modules/\n",
        encoding="utf-8",
    )
    (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (root / ".env").write_text("TOKEN=not-read\n", encoding="utf-8")
    (root / "ignored-a.py").write_text("a\n", encoding="utf-8")
    (root / "ignored-b.py").write_text("b\n", encoding="utf-8")
    (root / "node_modules" / "pkg" / "index.js").write_text(
        "module\n",
        encoding="utf-8",
    )
    return root


def test_preflight_is_metadata_only_stable_and_preserves_baseline_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    guarded_paths = {
        root / "app.py",
        root / ".env",
        root / "ignored-a.py",
        root / "ignored-b.py",
        root / "node_modules" / "pkg" / "index.js",
    }
    original_open = Path.open

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path in guarded_paths:
            raise AssertionError("preflight opened candidate content")
        return cast(IO[Any], original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", guarded_open)
    service = InventoryPreflightService()
    request = InventoryPreflightRequest(
        requested_paths=("node_modules", "app.py", "app.py"),
    )

    first = service.create("project:demo", root, request)
    second = service.create("project:demo", root, request)

    assert first.preflight_request_id == second.preflight_request_id
    assert first.candidate_set.inventory_policy_schema_version == (
        "scan-inventory-policy/v1"
    )
    assert first.candidate_set.inventory_policy_digest.startswith("sha256:")
    assert [item.target_path for item in first.requested_target_results] == [
        "app.py",
        "node_modules",
    ]
    outcomes = {
        item.path: item.base_outcome.value
        for item in first.candidate_set.candidates
    }
    assert outcomes["app.py"] == "included"
    assert outcomes[".env"] == "included"
    assert outcomes["ignored-a.py"] == "soft_excluded"


def test_preflight_proposals_group_required_optional_and_directory_targets(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(
            requested_paths=("app.py", "ignored-a.py", "node_modules"),
        ),
    )

    proposals = ScanBoundaryReviewService().create_selection_proposals(state)
    by_path = {item.target.path: item for item in proposals}

    assert by_path[".env"].selection_context is not None
    assert by_path[".env"].selection_context.review_kind == (
        "required_confirmation"
    )
    assert by_path["ignored-a.py"].selection_context is not None
    assert by_path["ignored-a.py"].selection_context.default_decision == (
        ScanBoundaryDecisionAction.SKIP_THIS_RUN
    )
    assert sum(item.target.path == "ignored-a.py" for item in proposals) == 1
    assert by_path["app.py"].selection_context is not None
    assert by_path["app.py"].selection_context.selection_scope == (
        "exact_file"
    )
    assert by_path["node_modules"].selection_context is not None
    assert by_path["node_modules"].selection_context.selection_scope == (
        "recursive_directory"
    )
    assert by_path["node_modules"].selection_context.directory_summary
    assert all(
        not item.evidence_packet.masked_evidence_values
        and not item.evidence_packet.masked_snippets
        for item in proposals
    )


def test_reviewable_page_cursor_is_bound_without_exposing_paths(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    service = InventoryPreflightService()
    state = service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )

    first_page = service.reviewable_excluded_page(state, limit=1)

    assert [item.path for item in first_page.items] == ["ignored-a.py"]
    assert first_page.next_cursor is not None
    assert "ignored" not in first_page.next_cursor
    second_page = service.reviewable_excluded_page(
        state,
        cursor=first_page.next_cursor,
        limit=1,
    )
    assert [item.path for item in second_page.items] == ["ignored-b.py"]

    other = service.create(
        "project:other",
        root,
        InventoryPreflightRequest(),
    )
    with pytest.raises(InventorySelectionError) as exc_info:
        service.reviewable_excluded_page(
            other,
            cursor=first_page.next_cursor,
            limit=1,
        )
    assert exc_info.value.code == InventorySelectionErrorCode.CURSOR_INVALID

    (root / "new.py").write_text("new\n", encoding="utf-8")
    changed = service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )
    with pytest.raises(InventorySelectionError) as changed_exc:
        service.reviewable_excluded_page(
            changed,
            cursor=first_page.next_cursor,
            limit=1,
        )
    assert changed_exc.value.code == InventorySelectionErrorCode.CURSOR_INVALID

    with pytest.raises(InventorySelectionError) as malformed_exc:
        service.reviewable_excluded_page(
            state,
            cursor="a",
            limit=1,
        )
    assert malformed_exc.value.code == (
        InventorySelectionErrorCode.CURSOR_INVALID
    )


def test_preflight_revalidation_detects_candidate_set_change(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    service = InventoryPreflightService()
    state = service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=("app.py",)),
    )
    target = state.requested_target_results[0].file_candidate
    assert target is not None
    decision = ScanBoundaryDecisionRequest(
        target_path="app.py",
        fingerprint=target.metadata_fingerprint,
        decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
    )
    (root / "app.py").write_text("print('changed size')\n", encoding="utf-8")

    with pytest.raises(InventorySelectionError) as exc_info:
        service.revalidate(
            "project:demo",
            root,
            state.preflight_request_id,
            (decision,),
        )

    assert exc_info.value.code == InventorySelectionErrorCode.PREFLIGHT_STALE
    assert exc_info.value.http_status == 409


def test_preflight_rejects_aggregate_directory_budget_without_partial_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    for dirname in ("one", "two"):
        (root / dirname).mkdir(parents=True)
        (root / dirname / "file.py").write_text("x\n", encoding="utf-8")
    service = InventoryPreflightService(max_aggregate_files=1)

    with pytest.raises(InventorySelectionError) as exc_info:
        service.create(
            "project:demo",
            root,
            InventoryPreflightRequest(requested_paths=("one", "two")),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED
    )
    assert exc_info.value.context == {
        "limit_kind": "aggregate_observed_file_count",
        "limit": 1,
        "observed_at_least": 2,
    }


def test_preflight_deduplicates_overlapping_directory_aggregate_budget(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    nested = root / "ignored" / "nested"
    nested.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (root / "ignored" / "one.py").write_text("1\n", encoding="utf-8")
    (nested / "two.py").write_text("2\n", encoding="utf-8")
    service = InventoryPreflightService(max_aggregate_files=2)

    state = service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(
            requested_paths=("ignored", "ignored/nested"),
        ),
    )

    assert len(state.requested_target_results) == 2
    assert all(
        item.directory_manifest is not None
        for item in state.requested_target_results
    )


def test_preflight_rejects_aggregate_directory_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    for dirname in ("one", "two"):
        (root / dirname).mkdir(parents=True)
        (root / dirname / "file.py").write_text("xx", encoding="utf-8")
    service = InventoryPreflightService(max_aggregate_bytes=3)

    with pytest.raises(InventorySelectionError) as exc_info:
        service.create(
            "project:demo",
            root,
            InventoryPreflightRequest(requested_paths=("one", "two")),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED
    )
    assert exc_info.value.context == {
        "limit_kind": "aggregate_selectable_bytes",
        "limit": 3,
        "observed_at_least": 4,
    }


def test_preflight_rejects_exact_5001_aggregate_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".gitignore").write_text("one/\ntwo/\n", encoding="utf-8")
    for dirname, count in (("one", 2_500), ("two", 2_501)):
        target = root / dirname
        target.mkdir()
        for index in range(count):
            (target / f"{index:04d}.py").touch()

    with pytest.raises(InventorySelectionError) as exc_info:
        InventoryPreflightService().create(
            "project:demo",
            root,
            InventoryPreflightRequest(requested_paths=("one", "two")),
        )

    assert exc_info.value.context == {
        "limit_kind": "aggregate_observed_file_count",
        "limit": 5_000,
        "observed_at_least": 5_001,
    }


def test_preflight_rejects_exact_500m_plus_one_aggregate_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".gitignore").write_text("one/\ntwo/\n", encoding="utf-8")
    one = root / "one"
    two = root / "two"
    one.mkdir()
    two.mkdir()
    for index in range(3):
        with (one / f"{index}.py").open("wb") as handle:
            handle.truncate(100_000_000)
    for index in range(2):
        with (two / f"{index}.py").open("wb") as handle:
            handle.truncate(100_000_000)
    (two / "plus-one.py").write_bytes(b"x")

    with pytest.raises(InventorySelectionError) as exc_info:
        InventoryPreflightService().create(
            "project:demo",
            root,
            InventoryPreflightRequest(requested_paths=("one", "two")),
        )

    assert exc_info.value.context == {
        "limit_kind": "aggregate_selectable_bytes",
        "limit": 500_000_000,
        "observed_at_least": 500_000_001,
    }


def test_preflight_allows_20_directory_scopes_and_rejects_21_before_walk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    paths = tuple(f"scope-{index:02d}" for index in range(21))
    for path in paths:
        (root / path).mkdir()
        (root / path / "file.py").write_text("x\n", encoding="utf-8")

    allowed = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(requested_paths=paths[:20]),
    )
    assert len(allowed.requested_target_results) == 20

    candidate_service = InventoryCandidateService()

    def fail_if_walked(*args: object, **kwargs: object) -> object:
        raise AssertionError("directory walker ran before scope limit")

    monkeypatch.setattr(
        candidate_service,
        "resolve_requested_path",
        fail_if_walked,
    )
    with pytest.raises(InventorySelectionError) as exc_info:
        InventoryPreflightService(candidate_service=candidate_service).create(
            "project:demo",
            root,
            InventoryPreflightRequest(requested_paths=paths),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.DIRECTORY_LIMIT_EXCEEDED
    )
    assert exc_info.value.context == {
        "limit_kind": "directory_scope_count",
        "limit": 20,
        "observed_at_least": 21,
    }


def test_default_inventory_over_5000_files_does_not_trigger_scope_limit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    source = root / "src"
    source.mkdir(parents=True)
    for index in range(5_001):
        (source / f"{index:04d}.py").touch()

    state = InventoryPreflightService().create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )

    assert len(state.candidate_set.candidates) == 5_001
    assert state.requested_target_results == ()


def test_preflight_fails_closed_over_200_required_reviews(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    for index in range(201):
        (root / f"secret-{index:03d}.txt").touch()

    with pytest.raises(InventorySelectionError) as exc_info:
        InventoryPreflightService().create(
            "project:demo",
            root,
            InventoryPreflightRequest(),
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.REVIEW_LIMIT_EXCEEDED
    )
    assert exc_info.value.context == {
        "limit": 200,
        "observed_at_least": 201,
    }


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_preflight_summary_counts_tracked_but_missing_candidate(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = root / "tracked.py"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "tracked.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked.unlink()
    service = InventoryPreflightService()

    state = service.create(
        "project:demo",
        root,
        InventoryPreflightRequest(),
    )

    assert service.summary(state).missing_count == 1
