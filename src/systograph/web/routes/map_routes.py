"""Read route for the latest controlled Markdown report artifact.

Building is not exposed here, and neither is reading the map. Scanning a
project into a new map goes through the project session flow
(`POST /api/projects/import` -> `POST /api/scans`); detail scan and apply
build on top of an existing scan. CLI `systograph map` covers the one-shot
scan-a-path case. Reading a map is build-scoped
(`GET /api/projects/{project_id}/map-builds/latest`,
`GET /api/map-builds/{build_id}`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from systograph.web.dependencies import session_store
from systograph.web.session_store import SessionStore

router = APIRouter(tags=["map"])


@router.get("/api/map/report")
def get_map_report(
    store: Annotated[SessionStore, Depends(session_store)],
    download: bool = False,
) -> Response:
    """Return the latest controlled Markdown report artifact."""
    result = store.latest_build_result()
    if result is None or result.map_markdown_path is None:
        raise HTTPException(
            status_code=404,
            detail="map_markdown_not_available",
        )
    if not result.map_markdown_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="map_markdown_not_available",
        )

    headers = {}
    if download:
        headers["Content-Disposition"] = (
            'attachment; filename="ai_system_map.md"'
        )
    return Response(
        content=result.map_markdown_path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )
