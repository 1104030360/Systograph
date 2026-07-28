"""Lock the app.state wiring contract before it gets refactored."""

from __future__ import annotations

from pathlib import Path

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
    pairs = (
        (dependencies.session_store, "session_store"),
        (dependencies.map_build_service, "map_build_service"),
        (dependencies.manual_mapping_service, "manual_mapping_service"),
        (dependencies.state_repository, "state_repository"),
        (dependencies.query_trace_service, "query_trace_service"),
    )
    for helper, attribute in pairs:
        resolved = helper(request)  # type: ignore[arg-type]
        assert resolved is getattr(local_api_app.state, attribute)
