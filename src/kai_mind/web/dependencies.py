"""FastAPI dependency helpers for local API routes."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
)
from kai_mind.core.services.build_commit_service import BuildCommitService
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.detail_scan_build_service import (
    DetailScanBuildService,
)
from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from kai_mind.core.services.inventory_selection_service import (
    InventorySelectionService,
)
from kai_mind.core.services.manual_mapping_service import (
    ManualMappingService,
)
from kai_mind.core.services.map_build_query_service import MapBuildQueryService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.session_store import SessionStore


def apply_confirmations_service(request: Request) -> ApplyConfirmationsService:
    return cast(
        ApplyConfirmationsService,
        request.app.state.apply_confirmations_service,
    )


def map_build_query_service(request: Request) -> MapBuildQueryService:
    return cast(
        MapBuildQueryService,
        request.app.state.map_build_query_service,
    )


def build_manifest_service(request: Request) -> BuildManifestService:
    return cast(BuildManifestService, request.app.state.build_manifest_service)


def build_commit_service(request: Request) -> BuildCommitService:
    return cast(BuildCommitService, request.app.state.build_commit_service)


def scan_snapshot_service(request: Request) -> ScanSnapshotService:
    return cast(ScanSnapshotService, request.app.state.scan_snapshot_service)


def inventory_preflight_service(request: Request) -> InventoryPreflightService:
    return cast(
        InventoryPreflightService,
        request.app.state.inventory_preflight_service,
    )


def inventory_selection_service(request: Request) -> InventorySelectionService:
    return cast(
        InventorySelectionService,
        request.app.state.inventory_selection_service,
    )


def state_repository(request: Request) -> LocalJsonStateProvider:
    return cast(LocalJsonStateProvider, request.app.state.state_repository)


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


def detail_scan_build_service(request: Request) -> DetailScanBuildService:
    return cast(
        DetailScanBuildService,
        request.app.state.detail_scan_build_service,
    )


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


def session_store(request: Request) -> SessionStore:
    return cast(SessionStore, request.app.state.session_store)
