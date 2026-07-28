"""Manual mapping routes for project-level confirmation decisions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingUpdate,
)
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.web.dependencies import manual_mapping_service
from kai_mind.web.legacy_mapping_guards import reject_legacy_mapping_type
from kai_mind.web.schemas import ManualMappingListResponse

router = APIRouter(prefix="/api", tags=["mappings"])


@router.get("/mappings", response_model=ManualMappingListResponse)
def list_mappings(
    project_id: str,
    service: Annotated[
        ManualMappingService,
        Depends(manual_mapping_service),
    ],
) -> ManualMappingListResponse:
    """Return project-level manual mapping decisions."""
    return ManualMappingListResponse(
        project_id=project_id,
        mappings=service.list_for_project(project_id),
    )


@router.post(
    "/mappings",
    response_model=ManualMapping,
    dependencies=[Depends(reject_legacy_mapping_type)],
)
def create_mapping(
    payload: ManualMappingCreate,
    service: Annotated[
        ManualMappingService,
        Depends(manual_mapping_service),
    ],
) -> ManualMapping:
    """Persist one manual mapping decision without mutating map artifacts."""
    try:
        return service.create_mapping(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/mappings/{mapping_id}",
    response_model=ManualMapping,
    dependencies=[Depends(reject_legacy_mapping_type)],
)
def update_mapping(
    mapping_id: str,
    payload: ManualMappingUpdate,
    service: Annotated[
        ManualMappingService,
        Depends(manual_mapping_service),
    ],
) -> ManualMapping:
    """Update one manual mapping decision."""
    try:
        return service.update_mapping(mapping_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="mapping_not_found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
