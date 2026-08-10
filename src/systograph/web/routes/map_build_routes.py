from __future__ import annotations

from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Response

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

# `file_name` -> (canonical name, MapBuildResult path field, media type).
# The whitelist is the only bridge from a caller-supplied name to a file:
# a name that is not a key here never reaches the filesystem, so path
# traversal has nothing to traverse. The canonical name is repeated in the
# value on purpose — `Content-Disposition` is then built from this table
# rather than from request text, so no future normalisation of the lookup
# can leak caller-shaped text into a header. Adding `.mmd` artifacts later
# is one more row (`system_map_mermaid_path` / `execution_map_mermaid_path`).
DOWNLOADABLE_BUILD_ARTIFACTS: Final[dict[str, tuple[str, str, str]]] = {
    "ai_system_map.md": (
        "ai_system_map.md",
        "map_markdown_path",
        "text/markdown; charset=utf-8",
    ),
}


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


@router.get("/api/map-builds/{build_id}/artifacts/{file_name}")
def get_build_artifact(
    build_id: str,
    file_name: str,
    service: Annotated[MapBuildQueryService, Depends(map_build_query_service)],
    download: bool = False,
) -> Response:
    """Return one whitelisted artifact of one build, content only.

    Resolving `build_id` + `file_name` to a real path happens entirely
    server-side; the response carries the file's bytes and headers, never
    the path it came from.
    """
    artifact = DOWNLOADABLE_BUILD_ARTIFACTS.get(file_name)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    artifact_name, path_field, media_type = artifact
    try:
        result = service.get(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="build_not_found") from exc
    # `BuildManifestService.load` already nulls paths that were gone at load
    # time, so a deleted artifact arrives here as `None`; the `is_file()`
    # arm covers the window between that load and this read.
    artifact_path: Path | None = getattr(result, path_field)
    if artifact_path is None or not artifact_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="artifact_not_available",
        )

    headers = {}
    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="{artifact_name}"'
        )
    # Bytes, not text: a text read would translate the build's newlines
    # (CRLF on Windows) and break byte identity with the published file.
    return Response(
        content=artifact_path.read_bytes(),
        media_type=media_type,
        headers=headers,
    )


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
