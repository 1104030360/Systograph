"""Query trace routes for explicit runtime endpoint probes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.trace import TraceRunResult
from kai_mind.core.services.query_trace_config_loader import (
    QueryTraceConfigError,
    QueryTraceConfigLoader,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.web.dependencies import query_trace_service, session_store
from kai_mind.web.schemas import TraceCreateRequest
from kai_mind.web.session_store import InMemorySessionStore

router = APIRouter(tags=["trace"])


@router.post("/api/trace", response_model=TraceRunResult)
def create_query_trace(
    payload: TraceCreateRequest,
    service: Annotated[QueryTraceService, Depends(query_trace_service)],
    store: Annotated[InMemorySessionStore, Depends(session_store)],
) -> TraceRunResult:
    """Run one explicit query against a validated map endpoint."""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    build_result = store.build_result(payload.project_id)
    if build_result is None or build_result.ai_system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")

    try:
        trace_config = QueryTraceConfigLoader().load_project_config(
            project.project_path
        )
    except QueryTraceConfigError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_trace_config: {exc}",
        ) from exc

    return service.trace(
        system_map=build_result.ai_system_map,
        endpoint_id=payload.endpoint_id,
        query=payload.query,
        timeout_seconds=payload.timeout_seconds,
        retrieved_chunks_keys=trace_config.retrieved_chunks_keys,
    )
