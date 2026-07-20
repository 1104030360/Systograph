"""Pending mapping proposal routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.mapping import (
    MappingProposal,
    MappingProposalDecisionResult,
)
from kai_mind.core.services.manual_mapping_support import template_slots
from kai_mind.core.services.mapping_evidence_packet_builder import (
    MappingEvidencePacketBuilder,
)
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.core.services.system_map_index import SystemMapIndex
from kai_mind.web.dependencies import (
    mapping_proposal_service,
    session_store,
)
from kai_mind.web.legacy_mapping_guards import reject_legacy_mapping_type
from kai_mind.web.schemas import (
    MappingProposalCreateRequest,
    MappingProposalDecisionRequest,
    MappingProposalListResponse,
)
from kai_mind.web.session_store import SessionStore

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
    store: Annotated[SessionStore, Depends(session_store)],
) -> MappingProposal:
    """Create a pending proposal from the latest masked map evidence."""
    if store.project(payload.project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    normalized = _normalized_map_for_project(store, payload.project_id)
    if normalized is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")

    index = SystemMapIndex.from_map(normalized)
    if index.unmapped_by_id(payload.source_unmapped_id) is None:
        raise HTTPException(status_code=404, detail="unmapped_not_found")

    confirmed_component_ids = [
        component.component_id
        for component in normalized.components
        if component.metadata.get("semantic_kind") == "repo_component"
    ]
    packet = MappingEvidencePacketBuilder().build(
        project_id=payload.project_id,
        index=index,
        unmapped_id=payload.source_unmapped_id,
        available_slots=sorted(template_slots()),
        confirmed_component_ids=confirmed_component_ids,
        user_description=payload.user_description,
    )
    try:
        return service.create_proposal(packet)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/mapping-proposals/{proposal_id}/decision",
    response_model=MappingProposalDecisionResult,
    dependencies=[Depends(reject_legacy_mapping_type)],
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


def _normalized_map_for_project(
    store: SessionStore,
    project_id: str,
) -> AiSystemMapV2 | None:
    result = store.build_result(project_id)
    if result is None or result.ai_system_map is None:
        return None
    return result.ai_system_map
