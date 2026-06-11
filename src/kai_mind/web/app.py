"""FastAPI application factory for the local KAI-Mind API."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from kai_mind.core.providers.llm_proposal_provider import (
    nvidia_nim_provider_from_env,
)
from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.middleware import (
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    RequestSizeLimitMiddleware,
    SafeUnhandledExceptionMiddleware,
)
from kai_mind.web.routes import (
    detail_scan_routes,
    map_routes,
    mapping_proposal_routes,
    mapping_routes,
    project_routes,
    scan_boundary_routes,
    scan_routes,
    trace_routes,
    viewer_routes,
)
from kai_mind.web.session_store import InMemorySessionStore

DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


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
    query_trace_service: QueryTraceService | None = None,
    scan_boundary_review_service: ScanBoundaryReviewService | None = None,
    viewer_session_service: ViewerSessionService | None = None,
    session_store: InMemorySessionStore | None = None,
    allowed_origins: Sequence[str] | None = None,
    env_file: Path | None = None,
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
) -> LocalApiApp:
    app = FastAPI(title="KAI-Mind Local API", version="0.1.0")
    app.state.manual_mapping_service = (
        manual_mapping_service or ManualMappingService()
    )
    app.state.mapping_proposal_service = (
        mapping_proposal_service
        or MappingProposalService(
            provider=nvidia_nim_provider_from_env(
                env_file=env_file or Path(".env"),
            ),
            manual_mapping_service=app.state.manual_mapping_service,
        )
    )
    app.state.scan_boundary_review_service = (
        scan_boundary_review_service or ScanBoundaryReviewService()
    )
    app.state.map_build_service = map_build_service or MapBuildService(
        manual_mapping_service=app.state.manual_mapping_service,
        scan_boundary_review_service=app.state.scan_boundary_review_service,
    )
    app.state.detail_scan_service = detail_scan_service or DetailScanService()
    app.state.query_trace_service = query_trace_service or QueryTraceService()
    app.state.viewer_session_service = (
        viewer_session_service or ViewerSessionService()
    )
    app.state.session_store = session_store or InMemorySessionStore()
    origins = tuple(allowed_origins or DEFAULT_ALLOWED_ORIGINS)
    app.add_middleware(SafeUnhandledExceptionMiddleware)
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_body_bytes=max_request_body_bytes,
    )
    app.include_router(map_routes.router)
    app.include_router(detail_scan_routes.router)
    app.include_router(mapping_proposal_routes.router)
    app.include_router(mapping_routes.router)
    app.include_router(project_routes.router)
    app.include_router(scan_boundary_routes.router)
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


app = create_app()
