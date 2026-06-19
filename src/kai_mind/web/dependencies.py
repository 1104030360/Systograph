"""FastAPI dependency helpers for local API routes."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.session_store import InMemorySessionStore


def map_build_service(request: Request) -> MapBuildService:
    return cast(MapBuildService, request.app.state.map_build_service)


def manual_mapping_service(request: Request) -> ManualMappingService:
    return cast(ManualMappingService, request.app.state.manual_mapping_service)


def mapping_proposal_service(request: Request) -> MappingProposalService:
    return cast(
        MappingProposalService,
        request.app.state.mapping_proposal_service,
    )


def detail_scan_service(request: Request) -> DetailScanService:
    return cast(DetailScanService, request.app.state.detail_scan_service)


def query_trace_service(request: Request) -> QueryTraceService:
    return cast(QueryTraceService, request.app.state.query_trace_service)


def scan_boundary_review_service(
    request: Request,
) -> ScanBoundaryReviewService:
    return cast(
        ScanBoundaryReviewService,
        request.app.state.scan_boundary_review_service,
    )


def viewer_session_service(request: Request) -> ViewerSessionService:
    return cast(
        ViewerSessionService,
        request.app.state.viewer_session_service,
    )


def session_store(request: Request) -> InMemorySessionStore:
    return cast(InMemorySessionStore, request.app.state.session_store)
