"""Scan session and progress event routes."""

from __future__ import annotations

import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.scan import OutputRun
from kai_mind.core.providers.local_json_state_errors import StateConflictError
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.web.dependencies import (
    build_manifest_service,
    map_build_service,
    scan_boundary_review_service,
    scan_snapshot_service,
    session_store,
    state_repository,
)
from kai_mind.web.schemas import (
    ScanCreateRequest,
    ScanCreateResponse,
    ScanProgressEvent,
)
from kai_mind.web.session_store import SessionStore

router = APIRouter(tags=["scans"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post(
    "/api/scans",
    response_model=ScanCreateResponse,
)
def create_scan(
    payload: ScanCreateRequest,
    service: Annotated[MapBuildService, Depends(map_build_service)],
    boundary_service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
    snapshot_service: Annotated[
        ScanSnapshotService,
        Depends(scan_snapshot_service),
    ],
    manifest_service: Annotated[
        BuildManifestService,
        Depends(build_manifest_service),
    ],
    repository: Annotated[
        LocalJsonStateProvider,
        Depends(state_repository),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> ScanCreateResponse:
    """用已匯入的 project_id 執行掃描，並回傳這次掃描的建置結果。"""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        inventory = snapshot_service.build_inventory(project.project_path)
        proposals = boundary_service.create_proposals(
            project_id=payload.project_id,
            project_root=project.project_path,
            inventory=inventory,
            decisions=payload.boundary_decisions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if proposals:
        return ScanCreateResponse(
            project_id=payload.project_id,
            status="requires_boundary_decision",
            boundary_proposals=proposals,
        )

    try:
        inventory_policy = boundary_service.for_decisions(
            project_id=payload.project_id,
            decisions=payload.boundary_decisions,
        )
        snapshot = snapshot_service.scan_and_save(
            project_id=payload.project_id,
            project_root=project.project_path,
            inventory_policy=inventory_policy,
            inventory=inventory,
            ua_analysis_result=None,
        )
        build_id = f"build:{uuid4()}"
        output_dir = Path(payload.output) / build_id.replace(":", "_")
        result = service.build_from_snapshot(
            snapshot,
            request=MapBuildRequest(
                project_path=project.project_path,
                output=Path(payload.output),
                redact_root_path=payload.redact_root_path,
                no_snippets=payload.no_snippets,
                system_map_schema_version=payload.system_map_schema_version,
            ),
            output_run=OutputRun(root_dir=output_dir),
            build_id=build_id,
            build_reason="initial_scan",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.status == "ok":
        pointer = repository.get_latest_pointer(payload.project_id)
        expected_id = pointer.latest_build_id if pointer else None
        expected_revision = pointer.revision if pointer else 0
        manifest_service.persist(result)
        try:
            repository.promote_latest_build(
                project_id=payload.project_id,
                build_id=build_id,
                expected_latest_build_id=expected_id,
                expected_revision=expected_revision,
            )
        except StateConflictError as exc:
            repository.discard_unpublished_build(
                payload.project_id,
                build_id,
            )
            if output_dir.is_dir():
                shutil.rmtree(output_dir)
            raise HTTPException(
                status_code=409,
                detail="latest_build_changed",
            ) from exc
        store.save_build_result(result, project_id=payload.project_id)
    return ScanCreateResponse(
        scan_id=snapshot.scan_id,
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
