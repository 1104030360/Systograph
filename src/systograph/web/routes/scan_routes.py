"""Scan session and progress event routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from systograph.core.models.errors import (
    InventoryEnumerationError,
    InventorySelectionError,
    InventorySelectionErrorCode,
    ScanInventoryRulesError,
)
from systograph.core.models.inventory_selection import (
    InventoryPreflightRequest,
)
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.scan import OutputRun
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.build_commit_service import (
    BuildCommitError,
    BuildCommitService,
)
from systograph.core.services.canonical_output_configuration import (
    CanonicalOutputConfigurationError,
    require_public_v2_selection,
)
from systograph.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from systograph.core.services.inventory_selection_service import (
    InventorySelectionService,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from systograph.core.services.scan_snapshot_service import ScanSnapshotService
from systograph.web.dependencies import (
    build_commit_service,
    inventory_preflight_service,
    inventory_selection_service,
    map_build_service,
    scan_boundary_review_service,
    scan_snapshot_service,
    session_store,
    state_repository,
)
from systograph.web.inventory_error_response import (
    inventory_error_detail,
    inventory_system_error_detail,
    project_not_found_detail,
)
from systograph.web.inventory_preflight_projection import (
    project_inventory_preflight,
)
from systograph.web.schemas import (
    InventoryPreflightApiRequest,
    InventoryPreflightResponse,
    ScanCreateRequest,
    ScanCreateResponse,
    ScanProgressEvent,
)
from systograph.web.session_store import (
    SessionStore,
    save_committed_build_projection,
)

router = APIRouter(tags=["scans"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post(
    "/api/projects/{project_id}/scan-preflights",
    response_model=InventoryPreflightResponse,
)
def create_scan_preflight(
    project_id: str,
    payload: InventoryPreflightApiRequest,
    preflight_service: Annotated[
        InventoryPreflightService,
        Depends(inventory_preflight_service),
    ],
    boundary_service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> InventoryPreflightResponse:
    project = store.project(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=project_not_found_detail(),
        )
    request = payload.to_core()
    try:
        state = preflight_service.create(
            project_id,
            project.project_path,
            request,
        )
        return project_inventory_preflight(
            state,
            request,
            preflight_service=preflight_service,
            boundary_service=boundary_service,
        )
    except InventorySelectionError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail=inventory_error_detail(exc),
        ) from exc
    except (InventoryEnumerationError, ScanInventoryRulesError) as exc:
        raise HTTPException(
            status_code=422,
            detail=inventory_system_error_detail(exc),
        ) from exc


@router.post(
    "/api/scans",
    response_model=ScanCreateResponse,
)
def create_scan(
    payload: ScanCreateRequest,
    service: Annotated[MapBuildService, Depends(map_build_service)],
    boundary_service: Annotated[
        ScanBoundaryReviewService,
        Depends(scan_boundary_review_service),
    ],
    selection_service: Annotated[
        InventorySelectionService,
        Depends(inventory_selection_service),
    ],
    preflight_service: Annotated[
        InventoryPreflightService,
        Depends(inventory_preflight_service),
    ],
    snapshot_service: Annotated[
        ScanSnapshotService,
        Depends(scan_snapshot_service),
    ],
    commit_service: Annotated[
        BuildCommitService,
        Depends(build_commit_service),
    ],
    repository: Annotated[
        LocalJsonStateProvider,
        Depends(state_repository),
    ],
    store: Annotated[SessionStore, Depends(session_store)],
) -> ScanCreateResponse:
    """用已匯入的 project_id 執行掃描，並回傳這次掃描的建置結果。"""
    project = store.project(payload.project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=project_not_found_detail(),
        )
    try:
        require_public_v2_selection(payload.system_map_schema_version)
    except CanonicalOutputConfigurationError as exc:
        raise HTTPException(status_code=422, detail=exc.code) from exc

    selection_summary = None
    try:
        explicit_preflight = payload.preflight_request_id is not None
        if explicit_preflight:
            selection_request_id = payload.preflight_request_id
        else:
            implicit_state = preflight_service.create(
                payload.project_id,
                project.project_path,
                InventoryPreflightRequest(
                    requested_paths=tuple(
                        item.target_path for item in payload.boundary_decisions
                    )
                ),
            )
            selection_request_id = implicit_state.preflight_request_id
            required_paths = {
                item.path
                for item in implicit_state.candidate_set.candidates
                if item.decision_required
            }
            if not payload.boundary_decisions and required_paths:
                implicit_proposals = (
                    boundary_service.create_selection_proposals(implicit_state)
                )
                return ScanCreateResponse(
                    project_id=payload.project_id,
                    status="requires_boundary_decision",
                    boundary_proposals=[
                        item
                        for item in implicit_proposals
                        if item.target.path in required_paths
                    ],
                )
            if any(
                item.target_path not in required_paths
                for item in payload.boundary_decisions
            ):
                raise InventorySelectionError(
                    InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED
                )
        assert selection_request_id is not None
        try:
            selection = selection_service.select(
                project_id=payload.project_id,
                project_root=project.project_path,
                preflight_request_id=selection_request_id,
                decisions=payload.boundary_decisions,
            )
        except InventorySelectionError as exc:
            if not explicit_preflight and exc.code in {
                InventorySelectionErrorCode.PREFLIGHT_STALE,
                InventorySelectionErrorCode.TARGET_CHANGED,
            }:
                refreshed = preflight_service.create(
                    payload.project_id,
                    project.project_path,
                    InventoryPreflightRequest(),
                )
                proposals = [
                    item
                    for item in boundary_service.create_selection_proposals(
                        refreshed
                    )
                    if item.selection_context is not None
                    and item.selection_context.decision_required
                ]
                if proposals:
                    return ScanCreateResponse(
                        project_id=payload.project_id,
                        status="requires_boundary_decision",
                        boundary_proposals=proposals,
                    )
            raise
        if selection.pending_proposals:
            return ScanCreateResponse(
                project_id=payload.project_id,
                status="requires_boundary_decision",
                boundary_proposals=list(selection.pending_proposals),
                preflight_request_id=payload.preflight_request_id,
            )
        if selection.inventory is None:
            raise ValueError("Inventory selection was not materialized")
        inventory = selection.inventory
        selection_summary = selection.summary
        proposals = []
    except InventorySelectionError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail=inventory_error_detail(exc),
        ) from exc
    except (InventoryEnumerationError, ScanInventoryRulesError) as exc:
        raise HTTPException(
            status_code=422,
            detail=inventory_system_error_detail(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if proposals:
        return ScanCreateResponse(
            project_id=payload.project_id,
            status="requires_boundary_decision",
            boundary_proposals=proposals,
            preflight_request_id=payload.preflight_request_id,
        )

    try:
        inventory_policy = None
        snapshot = snapshot_service.scan_and_save(
            project_id=payload.project_id,
            project_root=project.project_path,
            inventory_policy=inventory_policy,
            inventory=inventory,
            ua_analysis_result=None,
        )
        build_id = f"build:{uuid4()}"
        output_dir = Path(payload.output) / build_id.replace(":", "_")
        pointer = repository.get_latest_pointer(payload.project_id)
        expected_id = pointer.latest_build_id if pointer else None
        expected_revision = pointer.revision if pointer else 0

        def build(output_run: OutputRun) -> MapBuildResult:
            return service.build_from_snapshot(
                snapshot,
                request=MapBuildRequest(
                    project_path=project.project_path,
                    output=Path(payload.output),
                    redact_root_path=payload.redact_root_path,
                    no_snippets=payload.no_snippets,
                    system_map_schema_version=(
                        payload.system_map_schema_version
                    ),
                ),
                output_run=output_run,
                build_id=build_id,
                build_reason="initial_scan",
            )

        result = commit_service.commit(
            project_id=payload.project_id,
            build_id=build_id,
            final_output_dir=output_dir,
            expected_latest_build_id=expected_id,
            expected_revision=expected_revision,
            build=build,
        )
    except BuildCommitError as exc:
        status_code = (
            409
            if exc.code
            in {
                "build_output_conflict",
                "stale_latest_revision",
            }
            else 500
        )
        raise HTTPException(status_code=status_code, detail=exc.code) from exc
    except InventorySelectionError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail=inventory_error_detail(exc),
        ) from exc
    except (InventoryEnumerationError, ScanInventoryRulesError) as exc:
        raise HTTPException(
            status_code=422,
            detail=inventory_system_error_detail(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.status == "ok":
        result = save_committed_build_projection(
            store,
            result,
            project_id=payload.project_id,
        )
    return ScanCreateResponse(
        scan_id=snapshot.scan_id,
        project_id=payload.project_id,
        status="completed" if result.status == "ok" else "error",
        build_result=result,
        preflight_request_id=payload.preflight_request_id,
        inventory_selection_summary=selection_summary,
    )


@router.get("/api/scan/events", response_class=EventSourceResponse)
async def scan_events(response: Response) -> AsyncIterator[ServerSentEvent]:
    """送出目前的掃描進度 SSE 事件；現階段回傳一筆 completed 狀態。"""
    response.headers.update(SSE_HEADERS)
    event = ScanProgressEvent()
    yield ServerSentEvent(event=event.event, data=event)
