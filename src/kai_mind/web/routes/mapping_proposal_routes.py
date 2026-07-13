"""Pending mapping proposal routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.mapping import (
    MappingProposal,
    MappingProposalDecisionResult,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
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

    compatibility = _compatibility_projection(normalized)
    packet = MappingEvidencePacketBuilder().build(
        project_id=payload.project_id,
        index=index,
        unmapped_id=payload.source_unmapped_id,
        available_slots=compatibility["slots"],
        available_extensions=compatibility["extensions"],
        confirmed_component_ids=compatibility["components"],
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


def _normalized_map_for_project(
    store: SessionStore,
    project_id: str,
) -> AiSystemMapV2 | None:
    result = store.build_result(project_id)
    if result is None:
        return None
    if result.normalized_ai_system_map is not None:
        return result.normalized_ai_system_map
    if result.ai_system_map is None:
        return None
    return (
        CanonicalMapLoader()
        .load(result.ai_system_map.model_dump(mode="json"))
        .normalized
    )


def _compatibility_projection(
    system_map: AiSystemMapV2,
) -> dict[str, list[str]]:
    slots: list[str] = []
    extensions: list[str] = []
    components: list[str] = []
    for component in system_map.components:
        metadata = component.metadata
        slot = metadata.get("legacy_slot")
        extension = metadata.get("source_extension_id")
        semantic_kind = metadata.get("semantic_kind")
        if isinstance(slot, str):
            slots.append(slot)
        if isinstance(extension, str):
            extensions.append(extension)
        if semantic_kind == "repo_component":
            components.append(component.component_id)
    return {
        "slots": list(dict.fromkeys(slots)),
        "extensions": list(dict.fromkeys(extensions)),
        "components": list(dict.fromkeys(components)),
    }
