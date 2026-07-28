"""Lock the app.state wiring contract before it gets refactored."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from pathlib import Path

from fastapi import Request

from kai_mind.web import dependencies
from kai_mind.web.app import LocalApiApp, create_app

EXPECTED_STATE_ATTRIBUTES = frozenset(
    {
        "state_repository",
        "build_manifest_service",
        "build_commit_service",
        "state_dir",
        "manual_mapping_service",
        "mapping_proposal_service",
        "scan_boundary_review_service",
        "inventory_preflight_service",
        "inventory_selection_service",
        "map_build_service",
        "scan_snapshot_service",
        "apply_confirmations_service",
        "map_build_query_service",
        "detail_scan_service",
        "detail_scan_build_service",
        "query_trace_service",
        "viewer_session_service",
        "session_store",
    }
)

# 每個 web.dependencies 公開 helper 與它讀取的 app.state 屬性名。
# Plan 1 Task 3 整份改寫 dependencies.py 時，這裡是「16 個 helper
# 一個都不能接錯線」的驗收清單。
DEPENDENCY_HELPER_PAIRS: tuple[
    tuple[Callable[[Request], object], str], ...
] = (
    (
        dependencies.apply_confirmations_service,
        "apply_confirmations_service",
    ),
    (dependencies.map_build_query_service, "map_build_query_service"),
    (dependencies.build_manifest_service, "build_manifest_service"),
    (dependencies.build_commit_service, "build_commit_service"),
    (dependencies.scan_snapshot_service, "scan_snapshot_service"),
    (
        dependencies.inventory_preflight_service,
        "inventory_preflight_service",
    ),
    (
        dependencies.inventory_selection_service,
        "inventory_selection_service",
    ),
    (dependencies.state_repository, "state_repository"),
    (dependencies.map_build_service, "map_build_service"),
    (dependencies.manual_mapping_service, "manual_mapping_service"),
    (dependencies.mapping_proposal_service, "mapping_proposal_service"),
    (dependencies.detail_scan_build_service, "detail_scan_build_service"),
    (dependencies.query_trace_service, "query_trace_service"),
    (
        dependencies.scan_boundary_review_service,
        "scan_boundary_review_service",
    ),
    (dependencies.viewer_session_service, "viewer_session_service"),
    (dependencies.session_store, "session_store"),
)


def _names(functions: Iterable[object]) -> list[str]:
    return sorted(
        str(getattr(function, "__name__", function)) for function in functions
    )


def test_app_state_exposes_every_wired_service(
    local_api_app: LocalApiApp,
) -> None:
    for name in sorted(EXPECTED_STATE_ATTRIBUTES):
        assert getattr(local_api_app.state, name, None) is not None, name


def test_state_dir_is_the_injected_directory(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    app = create_app(state_dir=state_dir)
    assert app.state.state_dir == state_dir


def test_dependency_helpers_return_the_wired_instances(
    local_api_app: LocalApiApp,
) -> None:
    """每個 Depends helper 必須拿到 create_app 建的同一個物件。"""

    class _FakeRequest:
        def __init__(self, app: LocalApiApp) -> None:
            self.app = app

    request = _FakeRequest(local_api_app)
    for helper, attribute in DEPENDENCY_HELPER_PAIRS:
        resolved = helper(request)  # type: ignore[arg-type]
        assert resolved is getattr(local_api_app.state, attribute), attribute


def test_every_public_dependency_helper_is_under_contract() -> None:
    """新增 Depends helper 卻沒納入契約時，這條要紅。

    沒有這條的話，Plan 1 Task 3 改寫 dependencies.py 時新增的 helper
    會靜悄悄地逃出上面那份清單的保護。
    """
    declared = {
        value
        for name, value in vars(dependencies).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == dependencies.__name__
    }
    covered = {helper for helper, _ in DEPENDENCY_HELPER_PAIRS}

    assert _names(declared - covered) == []
    assert _names(covered - declared) == []
