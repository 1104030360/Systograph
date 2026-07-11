"""Viewer session routes for loading validated system maps."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from kai_mind.core.models.viewer import ViewerPayload
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.dependencies import session_store, viewer_session_service
from kai_mind.web.schemas import ViewerLoadMapRequest
from kai_mind.web.session_store import SessionStore

router = APIRouter(tags=["viewer"])


@router.post("/api/viewer/load", response_model=ViewerPayload)
def load_viewer_map(
    payload: ViewerLoadMapRequest,
    service: Annotated[
        ViewerSessionService,
        Depends(viewer_session_service),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> ViewerPayload:
    """Load an existing ai_system_map.json into the latest viewer session."""

    viewer_payload = ViewerPayload(
        viewer_load_result=service.load_map(Path(payload.map_json_path))
    )
    store.save_viewer_payload(viewer_payload)
    return viewer_payload
