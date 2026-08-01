"""Map build and viewer payload routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from systograph.core.models.map_build import MapBuildResult
from systograph.core.models.viewer import ViewerPayload
from systograph.core.services.canonical_output_configuration import (
    CanonicalOutputConfigurationError,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.web.dependencies import map_build_service, session_store
from systograph.web.schemas import MapBuildApiRequest
from systograph.web.session_store import SessionStore

router = APIRouter(tags=["map"])


@router.post("/api/map/build", response_model=MapBuildResult)
def build_map(
    payload: MapBuildApiRequest,
    service: Annotated[MapBuildService, Depends(map_build_service)],
    store: Annotated[SessionStore, Depends(session_store)],
) -> MapBuildResult:
    """掃描指定專案，產出 AI 系統地圖，並暫存最新的 viewer payload。"""
    try:
        result = service.build(payload.to_core_request())
    except CanonicalOutputConfigurationError as exc:
        raise HTTPException(status_code=422, detail=exc.code) from exc
    store.save_build_result(result)
    return result


@router.get("/api/map", response_model=ViewerPayload)
def get_api_map(
    store: Annotated[SessionStore, Depends(session_store)],
) -> ViewerPayload:
    """回傳目前暫存的 viewer payload，供前端讀取最新地圖狀態。"""
    return store.latest_viewer_payload()


@router.get("/api/map/report")
def get_map_report(
    store: Annotated[SessionStore, Depends(session_store)],
    download: bool = False,
) -> Response:
    """Return the latest controlled Markdown report artifact."""
    result = store.latest_build_result()
    if result is None or result.map_markdown_path is None:
        raise HTTPException(
            status_code=404,
            detail="map_markdown_not_available",
        )
    if not result.map_markdown_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="map_markdown_not_available",
        )

    headers = {}
    if download:
        headers["Content-Disposition"] = (
            'attachment; filename="ai_system_map.md"'
        )
    return Response(
        content=result.map_markdown_path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )


@router.get("/map", response_model=ViewerPayload)
def get_map_fallback(
    store: Annotated[SessionStore, Depends(session_store)],
) -> ViewerPayload:
    """提供 /api/map 的相同 payload，保留給舊版或簡化路徑使用。"""
    return store.latest_viewer_payload()
