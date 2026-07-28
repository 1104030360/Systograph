"""Detail scan routes for graph lazy loading."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from systograph.core.models.map_build import MapBuildResult
from systograph.core.models.system_map import DetailScanResult
from systograph.core.services.detail_scan_build_service import (
    DetailScanBuildError,
    DetailScanBuildService,
)
from systograph.core.services.detail_scan_service import (
    DetailScanService,
    DetailScanSnapshotStaleError,
)
from systograph.core.services.detail_scan_target_resolver import (
    DetailScanTargetError,
)
from systograph.core.services.viewer_session_service import (
    ViewerSessionService,
)
from systograph.web.dependencies import (
    detail_scan_build_service,
    detail_scan_service,
    session_store,
    viewer_session_service,
)
from systograph.web.schemas import DetailScanCreateRequest, DetailScanResponse
from systograph.web.session_store import (
    SessionStore,
    save_committed_build_projection,
)

router = APIRouter(tags=["detail-scans"])


@router.post("/api/detail-scans", response_model=DetailScanResponse)
def create_detail_scan(
    payload: DetailScanCreateRequest,
    service: Annotated[DetailScanService, Depends(detail_scan_service)],
    build_service: Annotated[
        DetailScanBuildService,
        Depends(detail_scan_build_service),
    ],
    viewer_service: Annotated[
        ViewerSessionService,
        Depends(viewer_session_service),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> DetailScanResponse:
    """Run a bounded target-scoped detail scan for the loaded project map."""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    build_result = store.build_result(payload.project_id)
    if (
        payload.build_id is None
        and build_result is not None
        and build_result.lineage is None
    ):
        return _legacy_detail_scan(
            payload,
            project_root=project.project_path,
            build_result=build_result,
            service=service,
            viewer_service=viewer_service,
            store=store,
        )

    try:
        result = build_service.run(
            project_id=payload.project_id,
            project_root=project.project_path,
            build_id=payload.build_id,
            target_type=payload.target_type,
            target=payload.target,
            scan_depth=payload.scan_depth,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="build_not_found") from exc
    except DetailScanSnapshotStaleError as exc:
        raise HTTPException(
            status_code=409,
            detail="scan_snapshot_stale",
        ) from exc
    except DetailScanBuildError as exc:
        detail = str(exc)
        status = (
            409
            if detail
            in {"base_build_not_latest", "profile_sidecar_unavailable"}
            else 404
        )
        raise HTTPException(status_code=status, detail=detail) from exc
    except DetailScanTargetError as exc:
        detail = str(exc) or "target_not_found"
        raise HTTPException(status_code=422, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    child = result.build_result
    if child.ai_system_map is None or child.viewer_load_result is None:
        raise HTTPException(status_code=500, detail="detail_build_incomplete")
    system_map = child.ai_system_map
    viewer = child.viewer_load_result
    child = save_committed_build_projection(
        store,
        child,
        project_id=payload.project_id,
    )

    return DetailScanResponse(
        project_id=payload.project_id,
        detail_scan=result.detail_scan,
        ai_system_map=system_map,
        source_build_id=result.source_build_id,
        build_id=child.lineage.build_id if child.lineage else None,
        scan_id=child.lineage.scan_id if child.lineage else None,
        viewer_load_result=viewer,
        warnings=list(dict.fromkeys((*result.warnings, *child.warnings))),
    )


@router.get(
    "/api/detail-scans/{detail_scan_id}",
    response_model=DetailScanResponse,
)
def get_detail_scan(
    detail_scan_id: str,
    store: Annotated[SessionStore, Depends(session_store)],
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
    store: SessionStore,
    detail_scan_id: str,
) -> tuple[str, MapBuildResult, DetailScanResult] | None:
    for project_id, build_result in store.build_results():
        system_map = build_result.ai_system_map
        if system_map is None:
            continue
        for detail_scan in build_result.detail_scan_results:
            if detail_scan.id == detail_scan_id:
                return project_id, build_result, detail_scan
    return None


def _legacy_detail_scan(
    payload: DetailScanCreateRequest,
    *,
    project_root: Path,
    build_result: MapBuildResult,
    service: DetailScanService,
    viewer_service: ViewerSessionService,
    store: SessionStore,
) -> DetailScanResponse:
    if build_result.ai_system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")
    try:
        result = service.scan(
            project_root=project_root,
            system_map=build_result.ai_system_map,
            target_type=payload.target_type,
            target=payload.target,
            scan_depth=payload.scan_depth,
        )
    except DetailScanTargetError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc) or "target_not_found",
        ) from exc
    viewer = viewer_service.build_canonical(
        result.system_map,
        map_json_path=build_result.map_json_path,
    )
    updated = build_result.model_copy(
        update={
            "ai_system_map": result.system_map,
            "viewer_load_result": viewer,
            "detail_scan_results": [
                *build_result.detail_scan_results,
                result.detail_scan,
            ],
        }
    )
    store.save_build_result(updated, project_id=payload.project_id)
    return DetailScanResponse(
        project_id=payload.project_id,
        detail_scan=result.detail_scan,
        ai_system_map=result.system_map,
        viewer_load_result=viewer,
        warnings=["legacy_latest_build_fallback"],
    )
