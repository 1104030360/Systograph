"""FastAPI application factory for the local KAI-Mind API."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.routes import (
    detail_scan_routes,
    map_routes,
    mapping_proposal_routes,
    mapping_routes,
    project_routes,
    scan_routes,
    viewer_routes,
)
from kai_mind.web.session_store import InMemorySessionStore

DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def create_app(
    *,
    map_build_service: MapBuildService | None = None,
    manual_mapping_service: ManualMappingService | None = None,
    mapping_proposal_service: MappingProposalService | None = None,
    detail_scan_service: DetailScanService | None = None,
    viewer_session_service: ViewerSessionService | None = None,
    session_store: InMemorySessionStore | None = None,
    allowed_origins: Sequence[str] | None = None,
    env_file: Path | None = None,
) -> FastAPI:
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
    app.state.map_build_service = map_build_service or MapBuildService(
        manual_mapping_service=app.state.manual_mapping_service
    )
    app.state.detail_scan_service = detail_scan_service or DetailScanService()
    app.state.viewer_session_service = (
        viewer_session_service or ViewerSessionService()
    )
    app.state.session_store = session_store or InMemorySessionStore()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins or DEFAULT_ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "PATCH", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    app.include_router(map_routes.router)
    app.include_router(detail_scan_routes.router)
    app.include_router(mapping_proposal_routes.router)
    app.include_router(mapping_routes.router)
    app.include_router(project_routes.router)
    app.include_router(scan_routes.router)
    app.include_router(viewer_routes.router)
    return app


app = create_app()
