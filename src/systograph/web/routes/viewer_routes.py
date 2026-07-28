"""Viewer session routes for loading validated system maps."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from systograph.core.models.viewer import ViewerPayload
from systograph.core.services.viewer_session_service import (
    ViewerSessionService,
)
from systograph.web.dependencies import session_store, viewer_session_service
from systograph.web.schemas import ViewerLoadMapRequest
from systograph.web.session_store import SessionStore

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
