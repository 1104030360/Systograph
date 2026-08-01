"""Project import routes for local path sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from systograph.web.dependencies import session_store
from systograph.web.schemas import (
    ProjectImportRequest,
    ProjectImportResponse,
    ProjectResponse,
)
from systograph.web.session_store import SessionStore

router = APIRouter(tags=["projects"])


@router.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    store: Annotated[SessionStore, Depends(session_store)],
) -> ProjectResponse:
    record = store.project(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return ProjectResponse(
        project_id=record.project_id,
        source_type="local_path",
        project_name=record.project_name,
    )


@router.post("/api/projects/import", response_model=ProjectImportResponse)
def import_project(
    payload: ProjectImportRequest,
    store: Annotated[SessionStore, Depends(session_store)],
) -> ProjectImportResponse:
    """登記本機專案路徑，建立 project_id，讓後續掃描可以引用。"""
    project_path = Path(payload.project_path)
    record = store.import_project(
        project_path=project_path,
        source_type=payload.source_type,
    )
    return ProjectImportResponse(
        project_id=record.project_id,
        source_type="local_path",
        project_name=record.project_name,
        project_path=str(record.project_path),
        reused=record.reused,
    )
