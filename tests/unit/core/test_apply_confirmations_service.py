from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import pytest

from kai_mind.core.models.analysis_history import (
    BuildReason,
    ProjectState,
    ScanSnapshot,
)
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
)
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.apply_confirmations_service import (
    ApplyConfirmationsService,
    ApplyValidationError,
    BaseBuildNotLatestError,
    BuildNotFoundError,
    MappingNotFoundError,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.manual_mapping_service import ManualMappingService
from kai_mind.core.services.map_build_service import MapBuildService


class BarrierMapBuildService(MapBuildService):
    def __init__(
        self,
        barrier: Barrier,
        manual_mapping_service: ManualMappingService,
    ) -> None:
        super().__init__(manual_mapping_service=manual_mapping_service)
        self._barrier = barrier

    def build_from_snapshot(
        self,
        snapshot: ScanSnapshot,
        *,
        request: MapBuildRequest,
        output_run: OutputRun,
        build_reason: BuildReason,
        build_id: str | None = None,
        based_on_build_id: str | None = None,
        mapping_ids: tuple[str, ...] = (),
    ) -> MapBuildResult:
        self._barrier.wait(timeout=10)
        return super().build_from_snapshot(
            snapshot,
            request=request,
            output_run=output_run,
            build_reason=build_reason,
            build_id=build_id,
            based_on_build_id=based_on_build_id,
            mapping_ids=mapping_ids,
        )


class FailingMapBuildService(MapBuildService):
    def build_from_snapshot(
        self,
        snapshot: ScanSnapshot,
        *,
        request: MapBuildRequest,
        output_run: OutputRun,
        build_reason: BuildReason,
        build_id: str | None = None,
        based_on_build_id: str | None = None,
        mapping_ids: tuple[str, ...] = (),
    ) -> MapBuildResult:
        raise RuntimeError("forced build failure")


def snapshot() -> ScanSnapshot:
    return ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(
            evidence=[
                Evidence(
                    id="evidence:retriever",
                    kind="code_pattern",
                    file="src/retriever.py",
                    path="Retriever.search",
                    line_start=1,
                    rule_id="retriever_rule",
                )
            ]
        ),
    )


def confirmed_draft(project_id: str = "project:demo") -> ManualMappingCreate:
    return ManualMappingCreate(
        project_id=project_id,
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id="unmapped:retriever",
        source_file="src/retriever.py",
        observed_kind="retriever",
        evidence_ids=["evidence:retriever"],
        target_slot="retriever",
        component_name="Demo Retriever",
    )


def setup_state(
    tmp_path: Path,
) -> tuple[
    LocalJsonStateProvider,
    ManualMappingService,
    ManualMapping,
    ApplyConfirmationsService,
]:
    state = LocalJsonStateProvider(tmp_path / "state")
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.save_project(
        ProjectState(
            project_id="project:demo",
            project_name="project",
            source_type="local_path",
            canonical_path=str(project_root),
            path_digest="sha256:path",
            created_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        )
    )
    source_snapshot = state.save_snapshot(snapshot())
    mappings = ManualMappingService(repository=state)
    builds = MapBuildService(manual_mapping_service=mappings)
    initial = builds.build_from_snapshot(
        source_snapshot,
        request=MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "output",
        ),
        output_run=OutputRun(root_dir=tmp_path / "output" / "build_b1"),
        build_id="build:b1",
        build_reason="initial_scan",
    )
    manifests = BuildManifestService(repository=state)
    manifests.persist(initial)
    state.promote_latest_build(
        project_id="project:demo",
        build_id="build:b1",
        expected_latest_build_id=None,
        expected_revision=0,
    )
    mapping = mappings.create_mapping(confirmed_draft())
    service = ApplyConfirmationsService(
        repository=state,
        map_build_service=builds,
        manifest_service=manifests,
    )
    return state, mappings, mapping, service


def test_apply_reuses_scan_and_creates_new_build(tmp_path: Path) -> None:
    state, _, mapping, service = setup_state(tmp_path)

    result = service.apply(
        base_build_id="build:b1",
        mapping_ids=(mapping.mapping_id,),
    )

    assert result.scan_id == "scan:s1"
    assert result.build_id != "build:b1"
    assert result.based_on_build_id == "build:b1"
    assert result.applied_mapping_ids == (mapping.mapping_id,)
    assert result.build_result.lineage is not None
    assert result.viewer_load_result.loaded
    assert state.get_latest_build_id("project:demo") == result.build_id


def test_repeated_apply_request_is_idempotent(tmp_path: Path) -> None:
    state, _, mapping, service = setup_state(tmp_path)

    first = service.apply(
        base_build_id="build:b1",
        mapping_ids=(mapping.mapping_id,),
    )
    second = service.apply(
        base_build_id="build:b1",
        mapping_ids=(mapping.mapping_id,),
    )

    assert second.build_id == first.build_id
    assert len(state.list_build_manifests("project:demo")) == 2


def test_apply_rejects_unknown_build_or_mapping(tmp_path: Path) -> None:
    _, _, mapping, service = setup_state(tmp_path)

    with pytest.raises(BuildNotFoundError):
        service.apply(
            base_build_id="build:missing",
            mapping_ids=(mapping.mapping_id,),
        )
    with pytest.raises(MappingNotFoundError):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=("mapping:missing",),
        )


def test_apply_rejects_invalid_decision_and_evidence(tmp_path: Path) -> None:
    _, mappings, _, service = setup_state(tmp_path)
    rejected = mappings.create_mapping(
        ManualMappingCreate.model_validate(
            {
                **confirmed_draft().model_dump(mode="json"),
                "decision": "rejected",
            }
        )
    )
    unknown_evidence = mappings.create_mapping(
        ManualMappingCreate.model_validate(
            {
                **confirmed_draft().model_dump(mode="json"),
                "evidence_ids": ["evidence:missing"],
            }
        )
    )

    with pytest.raises(ApplyValidationError, match="confirmed"):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=(rejected.mapping_id,),
        )
    with pytest.raises(ApplyValidationError, match="evidence"):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=(unknown_evidence.mapping_id,),
        )


def test_apply_rejects_mapping_from_another_project(tmp_path: Path) -> None:
    _, mappings, _, service = setup_state(tmp_path)
    foreign = mappings.create_mapping(confirmed_draft("project:other"))

    with pytest.raises(ApplyValidationError, match="another project"):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=(foreign.mapping_id,),
        )


def test_apply_rejects_stale_base_and_preserves_latest(tmp_path: Path) -> None:
    state, mappings, mapping, service = setup_state(tmp_path)
    applied = service.apply(
        base_build_id="build:b1",
        mapping_ids=(mapping.mapping_id,),
    )
    another = mappings.create_mapping(
        confirmed_draft().model_copy(update={"component_name": "Other"})
    )

    with pytest.raises(BaseBuildNotLatestError):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=(another.mapping_id,),
        )

    assert state.get_latest_build_id("project:demo") == applied.build_id


def test_apply_rejects_empty_or_duplicate_ids(tmp_path: Path) -> None:
    _, _, mapping, service = setup_state(tmp_path)

    with pytest.raises(ApplyValidationError):
        service.apply(base_build_id="build:b1", mapping_ids=())
    with pytest.raises(ApplyValidationError):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=(mapping.mapping_id, mapping.mapping_id),
        )


def test_concurrent_identical_apply_publishes_one_child(
    tmp_path: Path,
) -> None:
    state, mappings, mapping, _ = setup_state(tmp_path)
    builds = BarrierMapBuildService(
        Barrier(2),
        manual_mapping_service=mappings,
    )
    service = ApplyConfirmationsService(
        repository=state,
        map_build_service=builds,
        manifest_service=BuildManifestService(repository=state),
    )

    def invoke() -> str:
        return service.apply(
            base_build_id="build:b1",
            mapping_ids=(mapping.mapping_id,),
        ).build_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        build_ids = list(executor.map(lambda _index: invoke(), range(2)))

    assert len(set(build_ids)) == 1
    assert state.get_latest_build_id("project:demo") == build_ids[0]
    assert len(state.list_build_manifests("project:demo")) == 2


def test_apply_build_failure_preserves_latest_and_discards_output(
    tmp_path: Path,
) -> None:
    state, mappings, mapping, _ = setup_state(tmp_path)
    service = ApplyConfirmationsService(
        repository=state,
        map_build_service=FailingMapBuildService(
            manual_mapping_service=mappings
        ),
        manifest_service=BuildManifestService(repository=state),
        build_id_factory=lambda: "build:broken",
    )

    with pytest.raises(RuntimeError, match="forced build failure"):
        service.apply(
            base_build_id="build:b1",
            mapping_ids=(mapping.mapping_id,),
        )

    assert state.get_latest_build_id("project:demo") == "build:b1"
    assert state.find_build_manifest("build:broken") is None
    assert not (tmp_path / "output" / "build_broken").exists()
