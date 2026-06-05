"""Map build and viewer payload routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.viewer import ViewerPayload
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.web.dependencies import map_build_service, session_store
from kai_mind.web.schemas import MapBuildApiRequest
from kai_mind.web.session_store import InMemorySessionStore

router = APIRouter(tags=["map"])


@router.post("/api/map/build", response_model=MapBuildResult)
def build_map(
    payload: MapBuildApiRequest,
    service: Annotated[MapBuildService, Depends(map_build_service)],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> MapBuildResult:
    """掃描指定專案，產出 AI 系統地圖，並暫存最新的 viewer payload。"""
    result = service.build(payload.to_core_request())
    store.save_build_result(result)
    return result


@router.get("/api/map", response_model=ViewerPayload)
def get_api_map(
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> ViewerPayload:
    """回傳目前暫存的 viewer payload，供前端讀取最新地圖狀態。"""
    return store.latest_viewer_payload()


@router.get("/map", response_model=ViewerPayload)
def get_map_fallback(
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> ViewerPayload:
    """提供 /api/map 的相同 payload，保留給舊版或簡化路徑使用。"""
    return store.latest_viewer_payload()
