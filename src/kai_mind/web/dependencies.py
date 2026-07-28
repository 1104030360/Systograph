"""FastAPI dependency helpers for local API routes.

責任：把 `app.state` 上那個動態、無型別的容器換成一個 typed 的
`AppServices`，讓 route 的 `Depends(...)` 拿到的東西 mypy 檢查得到。

呼叫鏈：`web/app.py::create_app` → `app.state.services`（`AppServices`）
→ 本檔 `app_services(request)` → 各 helper → `routes/*` 的 `Depends`。

全檔只剩 `app_services` 這一處型別斷言——那是 Starlette state 動態本質
唯一需要斷言的邊界；跨過它之後全部都是 dataclass 的屬性存取，打錯字
（`map_biuld_service`）在 mypy 就會紅，不用等 route 執行才 AttributeError。
"""

from __future__ import annotations

from typing import cast

from fastapi import Request

from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
)
from kai_mind.core.services.build_commit_service import BuildCommitService
from kai_mind.core.services.detail_scan_build_service import (
    DetailScanBuildService,
)
from kai_mind.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from kai_mind.core.services.inventory_selection_service import (
    InventorySelectionService,
)
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.map_build_query_service import MapBuildQueryService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.app_services import AppServices
from kai_mind.web.session_store import SessionStore


def app_services(request: Request) -> AppServices:
    """Single untyped boundary: Starlette state is dynamic by design."""
    return cast(AppServices, request.app.state.services)


def apply_confirmations_service(request: Request) -> ApplyConfirmationsService:
    return app_services(request).apply_confirmations_service


def map_build_query_service(request: Request) -> MapBuildQueryService:
    return app_services(request).map_build_query_service


def build_commit_service(request: Request) -> BuildCommitService:
    return app_services(request).build_commit_service


def scan_snapshot_service(request: Request) -> ScanSnapshotService:
    return app_services(request).scan_snapshot_service


def inventory_preflight_service(request: Request) -> InventoryPreflightService:
    return app_services(request).inventory_preflight_service


def inventory_selection_service(request: Request) -> InventorySelectionService:
    return app_services(request).inventory_selection_service


def state_repository(request: Request) -> LocalJsonStateProvider:
    return app_services(request).state_repository


def map_build_service(request: Request) -> MapBuildService:
    return app_services(request).map_build_service


def manual_mapping_service(request: Request) -> ManualMappingService:
    return app_services(request).manual_mapping_service


def mapping_proposal_service(request: Request) -> MappingProposalService:
    return app_services(request).mapping_proposal_service


def detail_scan_build_service(request: Request) -> DetailScanBuildService:
    return app_services(request).detail_scan_build_service


def query_trace_service(request: Request) -> QueryTraceService:
    return app_services(request).query_trace_service


def scan_boundary_review_service(
    request: Request,
) -> ScanBoundaryReviewService:
    return app_services(request).scan_boundary_review_service


def viewer_session_service(request: Request) -> ViewerSessionService:
    return app_services(request).viewer_session_service


def session_store(request: Request) -> SessionStore:
    return app_services(request).session_store
