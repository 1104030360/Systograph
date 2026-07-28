"""FastAPI application factory for the local KAI-Mind API."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from kai_mind.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
)
from kai_mind.core.services.build_commit_service import BuildCommitService
from kai_mind.core.services.detail_scan_build_service import (
    DetailScanBuildService,
)
from kai_mind.core.services.detail_scan_service import DetailScanService
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
from kai_mind.web.app_services import build_app_services
from kai_mind.web.middleware import (
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    RequestSizeLimitMiddleware,
    SafeUnhandledExceptionMiddleware,
)
from kai_mind.web.routes import (
    detail_scan_routes,
    map_build_routes,
    map_routes,
    mapping_proposal_routes,
    mapping_routes,
    project_routes,
    scan_routes,
    trace_routes,
    viewer_routes,
)
from kai_mind.web.session_store import SessionStore

DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def default_state_dir() -> Path:
    configured = os.environ.get("KAI_MIND_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".kai-mind"


class LocalApiApp:
    """ASGI app wrapper that keeps FastAPI attributes discoverable in tests."""

    def __init__(
        self,
        inner_app: FastAPI,
        asgi_app: ASGIApp,
        *,
        allowed_origins: Sequence[str],
    ) -> None:
        self.app = inner_app
        self._asgi_app = asgi_app
        self.allowed_origins = tuple(allowed_origins)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await self._asgi_app(scope, receive, send)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.app, name)


def create_app(
    *,
    map_build_service: MapBuildService | None = None,
    manual_mapping_service: ManualMappingService | None = None,
    mapping_proposal_service: MappingProposalService | None = None,
    detail_scan_service: DetailScanService | None = None,
    detail_scan_build_service: DetailScanBuildService | None = None,
    query_trace_service: QueryTraceService | None = None,
    scan_boundary_review_service: ScanBoundaryReviewService | None = None,
    scan_snapshot_service: ScanSnapshotService | None = None,
    inventory_preflight_service: InventoryPreflightService | None = None,
    inventory_selection_service: InventorySelectionService | None = None,
    viewer_session_service: ViewerSessionService | None = None,
    session_store: SessionStore | None = None,
    state_dir: Path | None = None,
    apply_confirmations_service: ApplyConfirmationsService | None = None,
    map_build_query_service: MapBuildQueryService | None = None,
    build_commit_service: BuildCommitService | None = None,
    allowed_origins: Sequence[str] | None = None,
    env_file: Path | None = None,
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
) -> LocalApiApp:
    app = FastAPI(title="KAI-Mind Local API", version="0.1.0")
    if state_dir is None:
        state_dir = default_state_dir()
    services = build_app_services(
        state_dir=state_dir,
        map_build_service=map_build_service,
        manual_mapping_service=manual_mapping_service,
        mapping_proposal_service=mapping_proposal_service,
        detail_scan_service=detail_scan_service,
        detail_scan_build_service=detail_scan_build_service,
        query_trace_service=query_trace_service,
        scan_boundary_review_service=scan_boundary_review_service,
        scan_snapshot_service=scan_snapshot_service,
        inventory_preflight_service=inventory_preflight_service,
        inventory_selection_service=inventory_selection_service,
        viewer_session_service=viewer_session_service,
        session_store=session_store,
        apply_confirmations_service=apply_confirmations_service,
        map_build_query_service=map_build_query_service,
        build_commit_service=build_commit_service,
        env_file=env_file,
    )
    # app.state 上只掛這一個 typed 容器：routes 一律經
    # web/dependencies.py 的 helper 從它取服務，不再有平鋪的重複屬性。
    app.state.services = services
    # 走 typed 的 services.session_store（而不是 app.state 那個 Any）呼叫，
    # 讓 SessionStore Protocol 真的替這個呼叫做型別檢查。
    # 開機預熱一次：之後 GET /api/map 只讀快取，不會每個 request 重走
    # repository + 重載 artifact，而 POST /api/viewer/load 寫進去的
    # payload 也不再被磁碟上既有的 build 蓋掉。
    services.session_store.hydrate_from_latest()
    origins = tuple(allowed_origins or DEFAULT_ALLOWED_ORIGINS)
    # add_middleware 是 insert(0)，後掛的在外層。
    # 這個順序 = SafeUnhandledException 包住 RequestSizeLimit，
    # 讓 size limit 自身的例外也回統一的 JSON 錯誤格式。
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_body_bytes=max_request_body_bytes,
    )
    app.add_middleware(SafeUnhandledExceptionMiddleware)
    app.include_router(map_routes.router)
    app.include_router(map_routes.legacy_router)
    app.include_router(map_build_routes.router)
    app.include_router(detail_scan_routes.router)
    app.include_router(mapping_proposal_routes.router)
    app.include_router(mapping_routes.router)
    app.include_router(project_routes.router)
    app.include_router(scan_routes.router)
    app.include_router(trace_routes.router)
    app.include_router(viewer_routes.router)
    cors_wrapped_app = CORSMiddleware(
        app,
        allow_origins=list(origins),
        allow_credentials=False,
        allow_methods=["GET", "PATCH", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    return LocalApiApp(
        app,
        cors_wrapped_app,
        allowed_origins=origins,
    )
