"""Query trace routes for explicit runtime endpoint probes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from systograph.core.models.trace import TraceRunResult
from systograph.core.services.map_build_query_service import (
    MapBuildQueryService,
)
from systograph.core.services.query_trace_config_loader import (
    QueryTraceConfigError,
    QueryTraceConfigLoader,
)
from systograph.core.services.query_trace_service import QueryTraceService
from systograph.web.dependencies import (
    map_build_query_service,
    query_trace_service,
    session_store,
)
from systograph.web.schemas import TraceCreateRequest
from systograph.web.session_store import SessionStore

router = APIRouter(tags=["trace"])


@router.post("/api/trace", response_model=TraceRunResult)
def create_query_trace(
    payload: TraceCreateRequest,
    service: Annotated[QueryTraceService, Depends(query_trace_service)],
    build_query: Annotated[
        MapBuildQueryService,
        Depends(map_build_query_service),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> TraceRunResult:
    """Run one explicit query against a validated map endpoint."""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    try:
        build_result = (
            build_query.get(payload.build_id)
            if payload.build_id is not None
            else store.build_result(payload.project_id)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="build_not_found") from exc
    if build_result is None or build_result.ai_system_map is None:
        raise HTTPException(status_code=404, detail="map_not_loaded")
    if (
        build_result.lineage is not None
        and build_result.lineage.project_id != payload.project_id
    ):
        raise HTTPException(status_code=404, detail="build_not_found")

    try:
        trace_config = QueryTraceConfigLoader().load_project_config(
            project.project_path
        )
    except QueryTraceConfigError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_trace_config: {exc}",
        ) from exc

    result = service.trace(
        system_map=build_result.ai_system_map,
        endpoint_id=payload.endpoint_id,
        query=payload.query,
        timeout_seconds=payload.timeout_seconds,
        retrieved_chunks_keys=trace_config.retrieved_chunks_keys,
    )
    lineage = build_result.lineage
    warnings = list(result.warnings)
    if payload.build_id is None:
        warnings.append("latest_build_fallback")
    return result.model_copy(
        update={
            "source_scan_id": lineage.scan_id if lineage else None,
            "source_build_id": lineage.build_id if lineage else None,
            "warnings": warnings,
        }
    )
