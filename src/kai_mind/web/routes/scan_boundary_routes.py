"""Scan boundary proposal and decision routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.providers.filesystem_provider import FilesystemProvider
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.web.dependencies import (
    scan_boundary_review_service,
    session_store,
)
from kai_mind.web.schemas import (
    ScanBoundaryDecisionRequest,
    ScanBoundaryDecisionResult,
    ScanBoundaryProposalCreateRequest,
    ScanBoundaryProposalListResponse,
)
from kai_mind.web.session_store import InMemorySessionStore

router = APIRouter(tags=["scan-boundary-proposals"])


@router.get(
    "/api/scan-boundary-proposals",
    response_model=ScanBoundaryProposalListResponse,
)
def list_scan_boundary_proposals(
    project_id: str,
    service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> ScanBoundaryProposalListResponse:
    """Return project-level scan boundary proposal state."""

    if store.project(project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return ScanBoundaryProposalListResponse(
        project_id=project_id,
        proposals=service.list_for_project(project_id),
    )


@router.post(
    "/api/scan-boundary-proposals",
    response_model=ScanBoundaryProposalListResponse,
)
def create_scan_boundary_proposals(
    payload: ScanBoundaryProposalCreateRequest,
    service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> ScanBoundaryProposalListResponse:
    """Create pending scan boundary proposals from the latest project scan."""

    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    build_result = store.build_result(payload.project_id)
    if build_result is None or build_result.ai_system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")

    inventory = FilesystemProvider().build_inventory(project.project_path)
    try:
        proposals = service.create_proposals(
            project_id=payload.project_id,
            project_root=project.project_path,
            inventory=inventory,
            evidence=build_result.ai_system_map.evidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ScanBoundaryProposalListResponse(
        project_id=payload.project_id,
        proposals=proposals,
    )


@router.post(
    "/api/scan-boundary-proposals/{proposal_id}/decision",
    response_model=ScanBoundaryDecisionResult,
)
def decide_scan_boundary_proposal(
    proposal_id: str,
    payload: ScanBoundaryDecisionRequest,
    service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
) -> ScanBoundaryDecisionResult:
    """Save a user decision for future scan policy overlay."""

    try:
        return service.decide(proposal_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="proposal_not_found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
