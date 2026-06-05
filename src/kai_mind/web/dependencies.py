"""FastAPI dependency helpers for local API routes."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.web.session_store import InMemorySessionStore


def map_build_service(request: Request) -> MapBuildService:
    return cast(MapBuildService, request.app.state.map_build_service)


def session_store(request: Request) -> InMemorySessionStore:
    return cast(InMemorySessionStore, request.app.state.session_store)
