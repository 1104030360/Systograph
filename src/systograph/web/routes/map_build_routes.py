from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from systograph.core.providers.local_json_state_errors import (
    ProjectStateBusyError,
)
from systograph.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
    ApplyValidationError,
    BaseBuildNotLatestError,
    BuildNotFoundError,
    MappingNotFoundError,
)
from systograph.core.services.map_build_query_service import (
    MapBuildQueryService,
)
from systograph.web.dependencies import (
    apply_confirmations_service,
    map_build_query_service,
    session_store,
)
from systograph.web.schemas import (
    ApplyConfirmationsRequest,
    ApplyConfirmationsResponse,
    MapBuildHistoryResponse,
    MapBuildHistorySummary,
    MapBuildScopedResponse,
)
from systograph.web.session_store import (
    SessionStore,
    save_committed_build_projection,
)

router = APIRouter(tags=["map-builds"])


@router.post(
    "/api/map-builds/{base_build_id}/apply",
    response_model=ApplyConfirmationsResponse,
)
def apply_confirmations(
    base_build_id: str,
    payload: ApplyConfirmationsRequest,
    service: Annotated[
        ApplyConfirmationsService,
        Depends(apply_confirmations_service),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> ApplyConfirmationsResponse:
    try:
        result = service.apply(
            base_build_id=base_build_id,
            mapping_ids=tuple(payload.mapping_ids),
        )
    except (BuildNotFoundError, MappingNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BaseBuildNotLatestError as exc:
        raise HTTPException(
            status_code=409,
            detail="base_build_not_latest",
        ) from exc
    except ApplyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProjectStateBusyError as exc:
        raise HTTPException(
            status_code=503,
            detail="project_state_busy",
        ) from exc
    build_result = save_committed_build_projection(
        store,
        result.build_result,
        project_id=result.project_id,
    )
    result = result.model_copy(update={"build_result": build_result})
    return ApplyConfirmationsResponse.from_domain(result)


@router.get(
    "/api/map-builds/{build_id}",
    response_model=MapBuildScopedResponse,
)
def get_build(
    build_id: str,
    service: Annotated[MapBuildQueryService, Depends(map_build_query_service)],
) -> MapBuildScopedResponse:
    try:
        result = service.get(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="build_not_found") from exc
    return MapBuildScopedResponse.from_core(result)


@router.get(
    "/api/projects/{project_id}/map-builds/latest",
    response_model=MapBuildScopedResponse,
)
def get_latest_build(
    project_id: str,
    service: Annotated[MapBuildQueryService, Depends(map_build_query_service)],
) -> MapBuildScopedResponse:
    try:
        result = service.latest(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="build_not_found") from exc
    return MapBuildScopedResponse.from_core(result)


@router.get(
    "/api/projects/{project_id}/map-builds",
    response_model=MapBuildHistoryResponse,
)
def list_builds(
    project_id: str,
    service: Annotated[MapBuildQueryService, Depends(map_build_query_service)],
    store: Annotated[SessionStore, Depends(session_store)],
) -> MapBuildHistoryResponse:
    if store.project(project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return MapBuildHistoryResponse(
        project_id=project_id,
        builds=[
            MapBuildHistorySummary.from_manifest(item)
            for item in service.list(project_id)
        ],
    )
