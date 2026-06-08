"""Detail scan routes for graph lazy loading."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.system_map import DetailScanResult
from kai_mind.core.services.detail_scan_service import (
    DetailScanService,
    DetailScanTargetError,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.dependencies import (
    detail_scan_service,
    session_store,
    viewer_session_service,
)
from kai_mind.web.schemas import DetailScanCreateRequest, DetailScanResponse
from kai_mind.web.session_store import InMemorySessionStore

router = APIRouter(tags=["detail-scans"])


@router.post("/api/detail-scans", response_model=DetailScanResponse)
def create_detail_scan(
    payload: DetailScanCreateRequest,
    service: Annotated[DetailScanService, Depends(detail_scan_service)],
    viewer_service: Annotated[
        ViewerSessionService,
        Depends(viewer_session_service),
    ],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> DetailScanResponse:
    """Run a bounded target-scoped detail scan for the loaded project map."""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    build_result = store.build_result(payload.project_id)
    if build_result is None or build_result.ai_system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")

    try:
        result = service.scan(
            project_root=project.project_path,
            system_map=build_result.ai_system_map,
            target_type=payload.target_type,
            target=payload.target,
            scan_depth=payload.scan_depth,
        )
    except DetailScanTargetError as exc:
        detail = str(exc) or "target_not_found"
        raise HTTPException(status_code=422, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    viewer_payload = viewer_service.build(
        result.system_map,
        map_json_path=build_result.map_json_path,
    )
    updated_build_result = build_result.model_copy(
        update={
            "ai_system_map": result.system_map,
            "viewer_load_result": viewer_payload,
        }
    )
    store.save_build_result(
        updated_build_result,
        project_id=payload.project_id,
    )

    return DetailScanResponse(
        project_id=payload.project_id,
        detail_scan=result.detail_scan,
        ai_system_map=result.system_map,
    )


@router.get(
    "/api/detail-scans/{detail_scan_id}",
    response_model=DetailScanResponse,
)
def get_detail_scan(
    detail_scan_id: str,
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> DetailScanResponse:
    """Return one detail scan result from the latest loaded project map."""
    found = _find_detail_scan(store, detail_scan_id)
    if found is None:
        raise HTTPException(status_code=404, detail="detail_scan_not_found")
    project_id, build_result, detail_scan = found
    if build_result.ai_system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")
    return DetailScanResponse(
        project_id=project_id,
        detail_scan=detail_scan,
        ai_system_map=build_result.ai_system_map,
    )


def _find_detail_scan(
    store: InMemorySessionStore,
    detail_scan_id: str,
) -> tuple[str, MapBuildResult, DetailScanResult] | None:
    for project_id, build_result in store.build_results():
        system_map = build_result.ai_system_map
        if system_map is None:
            continue
        for detail_scan in system_map.detail_scans:
            if detail_scan.id == detail_scan_id:
                return project_id, build_result, detail_scan
    return None
