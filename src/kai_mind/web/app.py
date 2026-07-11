"""FastAPI application factory for the local KAI-Mind API."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from kai_mind.core.providers.llm_proposal_provider import (
    nvidia_nim_provider_from_env,
)
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.detail_scan_build_service import (
    DetailScanBuildService,
)
from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.map_build_query_service import MapBuildQueryService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.core.services.viewer_session_service import ViewerSessionService
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
from kai_mind.web.session_store import (
    PersistentSessionStore,
    SessionStore,
)

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
    viewer_session_service: ViewerSessionService | None = None,
    session_store: SessionStore | None = None,
    state_dir: Path | None = None,
    apply_confirmations_service: ApplyConfirmationsService | None = None,
    map_build_query_service: MapBuildQueryService | None = None,
    allowed_origins: Sequence[str] | None = None,
    env_file: Path | None = None,
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
) -> LocalApiApp:
    app = FastAPI(title="KAI-Mind Local API", version="0.1.0")
    if state_dir is None:
        state_dir = default_state_dir()
    repository = LocalJsonStateProvider(state_dir)
    manifest_service = BuildManifestService(repository=repository)
    app.state.state_repository = repository
    app.state.build_manifest_service = manifest_service
    app.state.state_dir = state_dir
    app.state.manual_mapping_service = (
        manual_mapping_service or ManualMappingService(repository=repository)
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
    shared_scanner = ProjectScanService()
    app.state.map_build_service = map_build_service or MapBuildService(
        project_scan_service=shared_scanner,
        manual_mapping_service=app.state.manual_mapping_service,
    )
    app.state.scan_snapshot_service = (
        scan_snapshot_service
        or ScanSnapshotService(
            project_scan_service=shared_scanner,
            repository=repository,
        )
    )
    app.state.apply_confirmations_service = (
        apply_confirmations_service
        or ApplyConfirmationsService(
            repository=repository,
            map_build_service=app.state.map_build_service,
            manifest_service=manifest_service,
        )
    )
    app.state.map_build_query_service = (
        map_build_query_service
        or MapBuildQueryService(
            repository=repository,
            manifest_service=manifest_service,
        )
    )
    app.state.detail_scan_service = detail_scan_service or DetailScanService()
    app.state.detail_scan_build_service = (
        detail_scan_build_service
        or DetailScanBuildService(
            detail_scan_service=app.state.detail_scan_service,
            map_build_service=app.state.map_build_service,
            query_service=app.state.map_build_query_service,
            manifest_service=manifest_service,
            repository=repository,
        )
    )
    app.state.query_trace_service = query_trace_service or QueryTraceService()
    app.state.viewer_session_service = (
        viewer_session_service or ViewerSessionService()
    )
    app.state.session_store = session_store or PersistentSessionStore(
        repository=repository,
        manifest_service=manifest_service,
        projection_service=app.state.viewer_session_service,
    )
    origins = tuple(allowed_origins or DEFAULT_ALLOWED_ORIGINS)
    app.add_middleware(SafeUnhandledExceptionMiddleware)
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_body_bytes=max_request_body_bytes,
    )
    app.include_router(map_routes.router)
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


app = create_app()
