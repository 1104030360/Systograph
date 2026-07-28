"""Query trace routes for explicit runtime endpoint probes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from kai_mind.core.models.trace import TraceRunResult
from kai_mind.core.services.logging_service import safe_log_event
from kai_mind.core.services.map_build_query_service import MapBuildQueryService
from kai_mind.core.services.query_trace_config_loader import (
    QueryTraceConfigError,
    QueryTraceConfigLoader,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.web.dependencies import (
    map_build_query_service,
    query_trace_service,
    session_store,
)
from kai_mind.web.schemas import TraceCreateRequest
from kai_mind.web.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["trace"])


@router.post("/trace", response_model=TraceRunResult)
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
        # 上游把 TOMLDecodeError / OSError 的訊息包進 exception，OSError
        # 那一側帶的是目標 pyproject.toml 的絕對路徑。回應只留穩定碼；
        # 診斷細節走 safe_log_event（會做 secret masking 與 path
        # redaction）進本機 log。
        safe_log_event(
            logger,
            logging.WARNING,
            "invalid_trace_config",
            stage="web_trace",
            project_id=payload.project_id,
            exception_type=exc.__class__.__name__,
            exc_info=exc,
        )
        raise HTTPException(
            status_code=400,
            detail="invalid_trace_config",
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
