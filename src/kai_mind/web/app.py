"""FastAPI application factory for the local KAI-Mind API."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.web.routes import map_routes, project_routes, scan_routes
from kai_mind.web.session_store import InMemorySessionStore

DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def create_app(
    *,
    map_build_service: MapBuildService | None = None,
    session_store: InMemorySessionStore | None = None,
    allowed_origins: Sequence[str] | None = None,
) -> FastAPI:
    app = FastAPI(title="KAI-Mind Local API", version="0.1.0")
    app.state.map_build_service = map_build_service or MapBuildService()
    app.state.session_store = session_store or InMemorySessionStore()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins or DEFAULT_ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    app.include_router(map_routes.router)
    app.include_router(project_routes.router)
    app.include_router(scan_routes.router)
    return app


app = create_app()
