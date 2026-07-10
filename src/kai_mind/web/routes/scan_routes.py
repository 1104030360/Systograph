"""Scan session and progress event routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.providers.filesystem_provider import FilesystemProvider
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.web.dependencies import (
    map_build_service,
    scan_boundary_review_service,
    session_store,
)
from kai_mind.web.schemas import (
    ScanCreateRequest,
    ScanCreateResponse,
    ScanProgressEvent,
)
from kai_mind.web.session_store import InMemorySessionStore

router = APIRouter(tags=["scans"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/api/scans", response_model=ScanCreateResponse)
def create_scan(
    payload: ScanCreateRequest,
    service: Annotated[MapBuildService, Depends(map_build_service)],
    boundary_service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> ScanCreateResponse:
    """用已匯入的 project_id 執行掃描，並回傳這次掃描的建置結果。"""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        inventory = FilesystemProvider().build_inventory(project.project_path)
        proposals = boundary_service.create_proposals(
            project_id=payload.project_id,
            project_root=project.project_path,
            inventory=inventory,
            decisions=payload.boundary_decisions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    scan_id = f"scan:{uuid4()}"
    if proposals:
        return ScanCreateResponse(
            scan_id=scan_id,
            project_id=payload.project_id,
            status="requires_boundary_decision",
            boundary_proposals=proposals,
        )

    try:
        result = service.build(
            MapBuildRequest(
                project_path=project.project_path,
                output=Path(payload.output),
                redact_root_path=payload.redact_root_path,
                no_snippets=payload.no_snippets,
                system_map_schema_version=payload.system_map_schema_version,
            ),
            project_id=payload.project_id,
            inventory_policy=boundary_service.for_decisions(
                project_id=payload.project_id,
                decisions=payload.boundary_decisions,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.save_build_result(result, project_id=payload.project_id)
    return ScanCreateResponse(
        scan_id=scan_id,
        project_id=payload.project_id,
        status="completed" if result.status == "ok" else "error",
        build_result=result,
    )


@router.get("/api/scan/events", response_class=EventSourceResponse)
async def scan_events(response: Response) -> AsyncIterator[ServerSentEvent]:
    """送出目前的掃描進度 SSE 事件；現階段回傳一筆 completed 狀態。"""
    response.headers.update(SSE_HEADERS)
    event = ScanProgressEvent()
    yield ServerSentEvent(event=event.event, data=event)
