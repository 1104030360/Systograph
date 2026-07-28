"""Lock the local API wiring contract: routes, container, dependencies.

這是全 repo 唯一刻意直接碰 `app.state` 的測試檔——它的職責就是釘住
「app 對外露出什麼」這件事本身。其他測試要拿內部服務請走
`tests/helpers/web.py`。
"""

from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Callable, Iterable
from pathlib import Path

from fastapi import Request
from fastapi.routing import APIRoute

from kai_mind.web import dependencies
from kai_mind.web.app import LocalApiApp, create_app
from kai_mind.web.app_services import AppServices

# 這 23 條 URL 是對外契約（前端 + scripts/trace_*.sh 都硬寫著它們）。
# 這份清單記錄現況，不規定現況：真的要新增/刪除 endpoint 時才動它，
# 重構 router 寫法時它必須一個字都不變。
EXPECTED_ROUTES = frozenset(
    {
        ("POST", "/api/map/build"),
        ("GET", "/api/map"),
        ("GET", "/api/map/report"),
        ("GET", "/map"),
        ("POST", "/api/map-builds/{base_build_id}/apply"),
        ("GET", "/api/map-builds/{build_id}"),
        ("GET", "/api/projects/{project_id}/map-builds/latest"),
        ("GET", "/api/projects/{project_id}/map-builds"),
        ("POST", "/api/detail-scans"),
        ("GET", "/api/detail-scans/{detail_scan_id}"),
        ("GET", "/api/mapping-proposals"),
        ("POST", "/api/mapping-proposals"),
        ("POST", "/api/mapping-proposals/{proposal_id}/decision"),
        ("GET", "/api/mappings"),
        ("POST", "/api/mappings"),
        ("PATCH", "/api/mappings/{mapping_id}"),
        ("GET", "/api/projects/{project_id}"),
        ("POST", "/api/projects/import"),
        ("POST", "/api/projects/{project_id}/scan-preflights"),
        ("POST", "/api/scans"),
        ("GET", "/api/scan/events"),
        ("POST", "/api/trace"),
        ("POST", "/api/viewer/load"),
    }
)

# `app.state` 上現在只有 `services` 一個屬性，型別是 AppServices；
# 下面這 18 個名字是它的欄位（不再是平鋪在 app.state 上的屬性）。
# 這份清單記錄現況也釘住現況：真的要增刪服務時才動它，
# 純粹搬動接線寫法時它必須一個字都不變。
EXPECTED_SERVICE_FIELDS = frozenset(
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

# 每個 web.dependencies 公開 helper 與它取用的 AppServices 欄位名。
# 這裡是「15 個 helper 一個都不能接錯線」的驗收清單。
# 18 個欄位裡有 3 個沒有 Depends helper（零 route 直接用它們）：
# state_dir、build_manifest_service、detail_scan_service——它們只是別的
# 服務建構時吃的材料，所以只出現在 EXPECTED_SERVICE_FIELDS。
DEPENDENCY_HELPER_PAIRS: tuple[
    tuple[Callable[[Request], object], str], ...
] = (
    (
        dependencies.apply_confirmations_service,
        "apply_confirmations_service",
    ),
    (dependencies.map_build_query_service, "map_build_query_service"),
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

# `app_services` 不是 Depends helper（零 route 用它），而是上面 15 個
# helper 共用的那一道邊界：它負責把 Starlette 的動態 state 斷言成
# AppServices，其餘 helper 只是在它回傳的 dataclass 上取欄位。
# 它沒有「對應的 state 屬性」可以配對，所以從反射清單裡明列排除；
# 排除的是這一個具名函式，不是整類函式，真的新增 Depends helper 時
# 下面那條 tripwire 仍然會紅。它本身的接線由
# test_dependency_helpers_return_the_wired_instances 直接驗。
CONTAINER_ACCESSORS = frozenset({dependencies.app_services})


def _names(functions: Iterable[object]) -> list[str]:
    return sorted(
        str(getattr(function, "__name__", function)) for function in functions
    )


def test_registered_routes_match_the_published_contract(
    local_api_app: LocalApiApp,
) -> None:
    """URL 是對外契約。改 router 寫法時這條必須維持全綠。"""
    actual = {
        (method, route.path)
        for route in local_api_app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }
    assert actual == EXPECTED_ROUTES


def test_app_state_exposes_the_typed_service_container(
    local_api_app: LocalApiApp,
) -> None:
    """app.state 只掛一個 typed 容器，且它每個欄位都接好了。"""
    services = local_api_app.state.services
    assert isinstance(services, AppServices)

    declared = {field.name for field in dataclasses.fields(AppServices)}
    assert declared == EXPECTED_SERVICE_FIELDS
    for name in sorted(EXPECTED_SERVICE_FIELDS):
        assert getattr(services, name) is not None, name

    # 平鋪的重複屬性已經拆掉了：唯一的入口就是上面那個容器。
    # 有人手滑把某個服務又掛回 app.state 時，這裡要紅。
    for name in sorted(EXPECTED_SERVICE_FIELDS):
        assert not hasattr(local_api_app.state, name), name


def test_state_dir_is_the_injected_directory(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    app = create_app(state_dir=state_dir)
    assert app.state.services.state_dir == state_dir


def test_dependency_helpers_return_the_wired_instances(
    local_api_app: LocalApiApp,
) -> None:
    """每個 Depends helper 必須拿到 create_app 建的同一個物件。"""

    class _FakeRequest:
        def __init__(self, app: LocalApiApp) -> None:
            self.app = app

    request = _FakeRequest(local_api_app)
    services = local_api_app.state.services
    # 所有 helper 共用的那道邊界：先確認它就是 create_app 掛上去的容器，
    # 下面 15 條配對才是在驗「從容器取對欄位」而不是在驗別的東西。
    assert (
        dependencies.app_services(request)  # type: ignore[arg-type]
        is services
    )
    for helper, field_name in DEPENDENCY_HELPER_PAIRS:
        resolved = helper(request)  # type: ignore[arg-type]
        assert resolved is getattr(services, field_name), field_name


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

    assert _names(declared - covered - CONTAINER_ACCESSORS) == []
    assert _names(covered - declared) == []
