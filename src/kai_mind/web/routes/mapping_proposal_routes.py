"""Pending mapping proposal routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.mapping import (
    MappingProposal,
    MappingProposalDecisionResult,
)
from kai_mind.core.models.system_map import RagSystemMap, UnmappedComponent
from kai_mind.core.services.mapping_evidence_packet_builder import (
    MappingEvidencePacketBuilder,
)
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.web.dependencies import (
    mapping_proposal_service,
    session_store,
)
from kai_mind.web.schemas import (
    MappingProposalCreateRequest,
    MappingProposalDecisionRequest,
    MappingProposalListResponse,
)
from kai_mind.web.session_store import InMemorySessionStore

router = APIRouter(tags=["mapping-proposals"])


@router.get(
    "/api/mapping-proposals",
    response_model=MappingProposalListResponse,
)
def list_mapping_proposals(
    project_id: str,
    service: Annotated[
        MappingProposalService,
        Depends(mapping_proposal_service),
    ],
) -> MappingProposalListResponse:
    """Return project-level pending proposal lifecycle state."""
    return MappingProposalListResponse(
        project_id=project_id,
        proposals=service.list_for_project(project_id),
    )


@router.post(
    "/api/mapping-proposals",
    response_model=MappingProposal,
)
def create_mapping_proposal(
    payload: MappingProposalCreateRequest,
    service: Annotated[
        MappingProposalService,
        Depends(mapping_proposal_service),
    ],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> MappingProposal:
    """Create a pending proposal from the latest masked map evidence."""
    system_map = _latest_system_map(store)
    if system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")
    if store.project(payload.project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    unmapped = _find_unmapped(system_map, payload.source_unmapped_id)
    if unmapped is None:
        raise HTTPException(status_code=404, detail="unmapped_not_found")

    packet = MappingEvidencePacketBuilder().build(
        project_id=payload.project_id,
        unmapped_component=unmapped,
        evidence=system_map.evidence,
        available_slots=list(system_map.components_by_slot),
        available_extensions=[
            extension.id for extension in system_map.extensions
        ],
        confirmed_component_ids=[
            instance.id
            for slot in system_map.components_by_slot.values()
            for instance in slot.instances
        ],
        user_description=payload.user_description,
    )
    try:
        return service.create_proposal(packet)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/mapping-proposals/{proposal_id}/decision",
    response_model=MappingProposalDecisionResult,
)
def decide_mapping_proposal(
    proposal_id: str,
    payload: MappingProposalDecisionRequest,
    service: Annotated[
        MappingProposalService,
        Depends(mapping_proposal_service),
    ],
) -> MappingProposalDecisionResult:
    """Apply a user decision to a pending proposal."""
    try:
        return service.decide(proposal_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="proposal_not_found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _latest_system_map(store: InMemorySessionStore) -> RagSystemMap | None:
    result = store.latest_build_result()
    if result is None:
        return None
    return result.ai_system_map


def _find_unmapped(
    system_map: RagSystemMap,
    unmapped_id: str,
) -> UnmappedComponent | None:
    for component in system_map.unmapped_components:
        if component.id == unmapped_id:
            return component
    return None
