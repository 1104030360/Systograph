from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pytest

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalProject,
)
from systograph.core.models.analysis_history import MapBuildLineage
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.scan import OutputRun
from systograph.core.services.build_artifact_publisher import (
    BuildArtifactPublisher,
)
from systograph.core.services.legacy_v1_rollback_service import (
    LegacyV1RollbackError,
    LegacyV1RollbackService,
)
from systograph.core.services.map_build_pipeline import MapBuildPipeline
from systograph.core.services.system_map_materialization_service import (
    SystemMapMaterializationService,
)
from systograph.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationService,
)

SourceSchemaVersion = Literal["ai-system-map/v1", "ai-system-map/v2"] | None


def _component(metadata: dict[str, Any]) -> CanonicalComponent:
    return CanonicalComponent(
        component_id="component:vector-store",
        display_name="Vector Store",
        canonical_type="vector_store",
        layer="retrieval",
        status="detected",
        activation="enabled",
        metadata=metadata,
    )


def _system_map(
    *,
    source_schema_version: SourceSchemaVersion,
    components: tuple[CanonicalComponent, ...] = (),
) -> AiSystemMapV2:
    return AiSystemMapV2(
        schema_version="ai-system-map/v2",
        system_type="ai_system",
        source_schema_version=source_schema_version,
        project=CanonicalProject(name="project"),
        components=list(components),
    )


def _rollback_service() -> LegacyV1RollbackService:
    return LegacyV1RollbackService(
        materialization_service=SystemMapMaterializationService()
    )


def _v1_pipeline() -> MapBuildPipeline:
    return MapBuildPipeline(
        materialization_service=SystemMapV2MaterializationService(),
        artifact_publisher=BuildArtifactPublisher(),
        canonical_output_version="ai-system-map/v1",
        legacy_v1_rollback_service=_rollback_service(),
    )


def _publish_existing_map(
    pipeline: MapBuildPipeline,
    *,
    system_map: AiSystemMapV2,
    project_root: Path,
    output_dir: Path,
) -> None:
    pipeline.materialize_existing_map(
        system_map=system_map,
        capability_candidates=(),
        request=MapBuildRequest(project_path=project_root),
        output_run=OutputRun(root_dir=output_dir),
        project_name="project",
        scan_id="scan:rollback",
        build_id="build:rollback",
        lineage=MapBuildLineage(
            project_id="project:rollback",
            scan_id="scan:rollback",
            build_id="build:rollback",
            based_on_build_id="build:parent",
            build_reason="detail_scan",
            generated_at=datetime(2026, 7, 28, tzinfo=UTC),
        ),
    )


@pytest.mark.parametrize(
    "source_schema_version",
    ["ai-system-map/v2", None],
)
def test_preflight_rejects_a_map_that_did_not_come_from_v1(
    source_schema_version: SourceSchemaVersion,
) -> None:
    """A natively built v2 map has no lossless v1 representation.

    Given a map whose source_schema_version is not ai-system-map/v1,
    When the rollback preflight runs,
    Then it raises legacy_rollback_not_representable, which is the code
    that means exactly "this map cannot be represented as v1".
    """
    with pytest.raises(
        LegacyV1RollbackError,
        match="legacy_rollback_not_representable",
    ):
        _rollback_service().require_representable(
            _system_map(source_schema_version=source_schema_version)
        )


def test_preflight_accepts_a_v1_sourced_map_with_legal_kinds() -> None:
    """The legacy contract can carry every compatibility semantic kind.

    Given a v1-sourced map whose components only use repo_component,
    slot_placeholder and legacy_extension,
    When the rollback preflight runs,
    Then it returns without raising, so the build may keep going.
    """
    system_map = _system_map(
        source_schema_version="ai-system-map/v1",
        components=tuple(
            _component({"semantic_kind": semantic_kind})
            for semantic_kind in (
                "repo_component",
                "slot_placeholder",
                "legacy_extension",
            )
        ),
    )

    # No exception is the assertion: the preflight accepted the map.
    _rollback_service().require_representable(system_map)


@pytest.mark.parametrize(
    "metadata",
    [
        pytest.param(
            {"semantic_kind": "reference_capability"},
            id="v2_only_semantic_kind",
        ),
        pytest.param(
            {"semantic_kind": "workflow_node"},
            id="workflow_semantic_kind",
        ),
        pytest.param({}, id="missing_semantic_kind"),
    ],
)
def test_preflight_rejects_a_component_outside_the_legacy_semantic_kinds(
    metadata: dict[str, Any],
) -> None:
    """v2-only components must fail closed instead of being dropped.

    Given a v1-sourced map holding a component whose semantic_kind is
    outside the legacy set (or missing entirely),
    When the rollback preflight runs,
    Then it raises legacy_rollback_not_representable so the rollback
    writer never silently loses that component.
    """
    system_map = _system_map(
        source_schema_version="ai-system-map/v1",
        components=(_component(metadata),),
    )

    with pytest.raises(
        LegacyV1RollbackError,
        match="legacy_rollback_not_representable",
    ):
        _rollback_service().require_representable(system_map)


def test_rollback_mode_rejects_the_detail_scan_rebuild_entry_point(
    tmp_path: Path,
) -> None:
    """Rollback mode cannot rebuild from an already enriched map.

    Given operator rollback mode and a representable v1-sourced map,
    When the enriched-map entry point is used,
    Then it raises legacy_rollback_detail_scan_unsupported — the honest
    code for "rollback has no enriched-map writer" — and writes nothing.
    """
    output_dir = tmp_path / "build"
    system_map = _system_map(
        source_schema_version="ai-system-map/v1",
        components=(_component({"semantic_kind": "repo_component"}),),
    )

    with pytest.raises(
        LegacyV1RollbackError,
        match="legacy_rollback_detail_scan_unsupported",
    ):
        _publish_existing_map(
            _v1_pipeline(),
            system_map=system_map,
            project_root=tmp_path / "project",
            output_dir=output_dir,
        )

    assert not output_dir.exists()


def test_rollback_detail_scan_reports_preflight_failures_first(
    tmp_path: Path,
) -> None:
    """The representability preflight still runs before that refusal.

    Given operator rollback mode and a natively built v2 map,
    When the enriched-map entry point is used,
    Then the preflight code wins over the unsupported-rebuild code, so
    operators still learn why the map itself is unusable.
    """
    output_dir = tmp_path / "build"

    with pytest.raises(
        LegacyV1RollbackError,
        match="legacy_rollback_not_representable",
    ):
        _publish_existing_map(
            _v1_pipeline(),
            system_map=_system_map(source_schema_version="ai-system-map/v2"),
            project_root=tmp_path / "project",
            output_dir=output_dir,
        )

    assert not output_dir.exists()
