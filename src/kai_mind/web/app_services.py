"""Typed container and factory for local API application services.

責任：把 `create_app()` 原本 90 行的 `x or Default()` 組裝搬到一個
mypy strict 檢查得到的地方——`AppServices(...)` 建構時每個欄位都被逐一
比對型別，放錯物件在這裡就會紅，而不是等 route 執行才 `AttributeError`。

呼叫鏈：`web/app.py::create_app` → `build_app_services()` → `AppServices`
（`create_app` 再把它掛到 `app.state`，routes 經 `web/dependencies.py` 取用）。

這裡只做**純物件組裝**，不做任何啟動動作：`hydrate_from_latest()` 之類的
預熱留在 `create_app()`，這樣「接線」與「開機」兩件事各自可以單獨測。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.providers.llm_proposal_provider import (
    nvidia_nim_provider_from_env,
)
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
)
from kai_mind.core.services.build_commit_service import BuildCommitService
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.canonical_output_configuration import (
    canonical_output_version_from_env,
)
from kai_mind.core.services.detail_scan_build_service import (
    DetailScanBuildService,
)
from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.inventory_candidate_service import (
    InventoryCandidateService,
)
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
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.core.services.scan_boundary_review_service import (
    ScanBoundaryReviewService,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.core.services.viewer_session_service import ViewerSessionService
from kai_mind.web.session_store import (
    PersistentSessionStore,
    SessionStore,
)


@dataclass(frozen=True, slots=True)
class AppServices:
    """Every service the local API needs, resolved and typed."""

    state_dir: Path
    state_repository: LocalJsonStateProvider
    build_manifest_service: BuildManifestService
    build_commit_service: BuildCommitService
    manual_mapping_service: ManualMappingService
    mapping_proposal_service: MappingProposalService
    scan_boundary_review_service: ScanBoundaryReviewService
    inventory_preflight_service: InventoryPreflightService
    inventory_selection_service: InventorySelectionService
    map_build_service: MapBuildService
    scan_snapshot_service: ScanSnapshotService
    apply_confirmations_service: ApplyConfirmationsService
    map_build_query_service: MapBuildQueryService
    detail_scan_service: DetailScanService
    detail_scan_build_service: DetailScanBuildService
    query_trace_service: QueryTraceService
    viewer_session_service: ViewerSessionService
    session_store: SessionStore


def build_app_services(
    *,
    state_dir: Path,
    map_build_service: MapBuildService | None = None,
    manual_mapping_service: ManualMappingService | None = None,
    mapping_proposal_service: MappingProposalService | None = None,
    detail_scan_service: DetailScanService | None = None,
    detail_scan_build_service: DetailScanBuildService | None = None,
    query_trace_service: QueryTraceService | None = None,
    scan_boundary_review_service: ScanBoundaryReviewService | None = None,
    scan_snapshot_service: ScanSnapshotService | None = None,
    inventory_preflight_service: InventoryPreflightService | None = None,
    inventory_selection_service: InventorySelectionService | None = None,
    viewer_session_service: ViewerSessionService | None = None,
    session_store: SessionStore | None = None,
    apply_confirmations_service: ApplyConfirmationsService | None = None,
    map_build_query_service: MapBuildQueryService | None = None,
    build_commit_service: BuildCommitService | None = None,
    env_file: Path | None = None,
) -> AppServices:
    """Resolve every service, honouring injected overrides.

    建構順序有相依性（後面的服務吃前面的實例），不要重排。
    """
    canonical_output_version = canonical_output_version_from_env()
    repository = LocalJsonStateProvider(state_dir)
    manifest_service = BuildManifestService(repository=repository)
    commit_service = build_commit_service or BuildCommitService(
        repository=repository,
        manifest_service=manifest_service,
    )
    resolved_manual_mapping = manual_mapping_service or ManualMappingService(
        repository=repository
    )
    resolved_proposal = mapping_proposal_service or MappingProposalService(
        provider=nvidia_nim_provider_from_env(
            env_file=env_file or Path(".env"),
        ),
        manual_mapping_service=resolved_manual_mapping,
    )
    resolved_boundary_review = (
        scan_boundary_review_service or ScanBoundaryReviewService()
    )
    if inventory_preflight_service is not None:
        resolved_preflight = inventory_preflight_service
    elif (
        # 刻意讀「參數」而非組好的 resolved_snapshot：預設路徑因此會產生
        # 兩個各自獨立、讀同一份 TOML 的 ScanInventoryRuleLoader。
        # 行為與重構前一致，要改請另開 plan。
        scan_snapshot_service is not None
        and scan_snapshot_service.inventory_rule_loader is not None
    ):
        resolved_preflight = InventoryPreflightService(
            candidate_service=InventoryCandidateService(
                inventory_rule_loader=(
                    scan_snapshot_service.inventory_rule_loader
                )
            )
        )
    else:
        resolved_preflight = InventoryPreflightService()
    resolved_selection = (
        inventory_selection_service
        or InventorySelectionService(preflight_service=resolved_preflight)
    )
    # 只有兩個預設實例才真的共用它：map_build_service 或
    # scan_snapshot_service 任一被注入時，共用就沒了。
    # 行為與重構前一致，要改請另開 plan。
    shared_scanner = ProjectScanService()
    resolved_map_build = map_build_service or MapBuildService(
        project_scan_service=shared_scanner,
        manual_mapping_service=resolved_manual_mapping,
        canonical_output_version=canonical_output_version,
    )
    resolved_snapshot = scan_snapshot_service or ScanSnapshotService(
        project_scan_service=shared_scanner,
        repository=repository,
    )
    resolved_apply = apply_confirmations_service or ApplyConfirmationsService(
        repository=repository,
        map_build_service=resolved_map_build,
        manifest_service=manifest_service,
        build_commit_service=commit_service,
    )
    resolved_query = map_build_query_service or MapBuildQueryService(
        repository=repository,
        manifest_service=manifest_service,
    )
    resolved_detail_scan = detail_scan_service or DetailScanService()
    resolved_detail_build = (
        detail_scan_build_service
        or DetailScanBuildService(
            detail_scan_service=resolved_detail_scan,
            map_build_service=resolved_map_build,
            query_service=resolved_query,
            manifest_service=manifest_service,
            repository=repository,
            build_commit_service=commit_service,
        )
    )
    resolved_trace = query_trace_service or QueryTraceService()
    resolved_viewer_session = viewer_session_service or ViewerSessionService()
    resolved_session_store = session_store or PersistentSessionStore(
        repository=repository,
        manifest_service=manifest_service,
        projection_service=resolved_viewer_session,
    )
    return AppServices(
        state_dir=state_dir,
        state_repository=repository,
        build_manifest_service=manifest_service,
        build_commit_service=commit_service,
        manual_mapping_service=resolved_manual_mapping,
        mapping_proposal_service=resolved_proposal,
        scan_boundary_review_service=resolved_boundary_review,
        inventory_preflight_service=resolved_preflight,
        inventory_selection_service=resolved_selection,
        map_build_service=resolved_map_build,
        scan_snapshot_service=resolved_snapshot,
        apply_confirmations_service=resolved_apply,
        map_build_query_service=resolved_query,
        detail_scan_service=resolved_detail_scan,
        detail_scan_build_service=resolved_detail_build,
        query_trace_service=resolved_trace,
        viewer_session_service=resolved_viewer_session,
        session_store=resolved_session_store,
    )
