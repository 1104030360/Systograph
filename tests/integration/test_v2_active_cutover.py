from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.scan import OutputRun, ProjectScanResult
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.build_manifest_service import (
    BuildManifestService,
)
from systograph.core.services.canonical_map_loader import (
    CanonicalMapLoader,
    CanonicalMapLoadError,
)
from systograph.core.services.canonical_output_configuration import (
    CanonicalOutputConfigurationError,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.rag_template_service import RagTemplateService
from systograph.web.app import create_app


def _build(
    tmp_path: Path,
    *,
    request: MapBuildRequest | None = None,
) -> MapBuildResult:
    snapshot = ScanSnapshot(
        project_id="project:v2-cutover",
        scan_id="scan:v2-cutover",
        generated_at=datetime(2026, 7, 17, tzinfo=UTC),
        inventory_digest="sha256:v2-cutover",
        scan_result=ProjectScanResult(),
    )
    return MapBuildService().build_from_snapshot(
        snapshot,
        request=request or MapBuildRequest(project_path=tmp_path / "project"),
        output_run=OutputRun(root_dir=tmp_path / "build"),
        build_reason="initial_scan",
        build_id="build:v2-cutover",
    )


def _build_fixture_project(
    tmp_path: Path,
    fixture_name: str,
    *,
    project_id: str | None = None,
) -> MapBuildResult:
    return MapBuildService().build(
        MapBuildRequest(
            project_path=rag_project_fixture_path(fixture_name),
            output=tmp_path / "outputs",
        ),
        project_id=project_id,
    )


def test_normal_v2_build_populates_recommended_next_checks(
    tmp_path: Path,
) -> None:
    """Recommended next checks survive on the active v2 build path.

    Given a scanned project that uses an external embedding provider, a
    secret-like config key and a published container port,
    When a normal ai-system-map/v2 build runs,
    Then every canonical check resolves to one of the four contracted
    target types (component instance / slot / endpoint, plus the
    system-wide fallback) with a target that exists in this map, at
    least one check stays evidence-targeted rather than system-wide,
    and the published artifact JSON round-trips that list unchanged.
    """
    # Given / When
    result = _build_fixture_project(tmp_path, "pgvector_openai_rag")

    # Then
    assert result.status == "ok"
    assert result.ai_system_map is not None
    system_map = result.ai_system_map
    checks = system_map.recommended_next_checks
    assert checks

    component_ids = {
        component.component_id for component in system_map.components
    }
    privacy_targets = {
        (check.target_type, check.target)
        for check in checks
        if check.id.startswith("check:privacy_exposure:")
    }
    runtime_targets = {
        (check.target_type, check.target)
        for check in checks
        if check.id.startswith("check:runtime_readiness:")
    }
    trust_targets = {
        (check.target_type, check.target)
        for check in checks
        if check.id.startswith("check:rag_knowledge_trust:")
    }
    assert (
        "component_instance",
        "component:vector_store:pgvector",
    ) in privacy_targets
    assert (
        "component_instance",
        "component:embedding_model:openai",
    ) in runtime_targets
    assert ("component_slot", "data_sources") in trust_targets

    # Whole-list target contract (MODEL-CONTRACT §5.3). Filtering to one
    # target type here would let an unresolved or unknown target slip
    # through unasserted, which is how the `system` fallback stayed
    # invisible; assert every check instead.
    endpoint_ids = {endpoint.endpoint_id for endpoint in system_map.endpoints}
    slot_ids = {
        slot.id for slot in RagTemplateService.load("rag-core-v1").slots
    }
    targets_by_type: dict[str, set[str]] = {}
    for check in checks:
        targets_by_type.setdefault(check.target_type, set()).add(check.target)
    assert targets_by_type.keys() <= {
        "component_instance",
        "component_slot",
        "endpoint",
        "system",
    }
    assert targets_by_type.get("component_instance", set()) <= component_ids
    assert targets_by_type.get("component_slot", set()) <= slot_ids
    assert targets_by_type.get("endpoint", set()) <= endpoint_ids
    assert targets_by_type.get("system", set()) <= {"system"}
    # Precision guard: the list must never degrade to system-wide only.
    assert targets_by_type.keys() - {"system"}

    assert all(check.reason and check.action for check in checks)
    assert [check.id for check in checks] == sorted(
        check.id for check in checks
    )

    assert result.map_json_path is not None
    payload = json.loads(result.map_json_path.read_text(encoding="utf-8"))
    dumped = system_map.model_dump(mode="json")
    dumped_checks = dumped["recommended_next_checks"]
    assert payload["recommended_next_checks"] == dumped_checks
    assert (
        AiSystemMapV2.model_validate(dumped).recommended_next_checks == checks
    )
    assert (
        CanonicalMapLoader().load(payload).normalized.recommended_next_checks
        == checks
    )


def test_reloaded_build_still_projects_recommended_next_checks(
    tmp_path: Path,
) -> None:
    """Checks live in the published artifact, not in scan memory.

    Given a built project whose canonical map carries recommended next
    checks,
    When the same build is re-loaded from disk via
    BuildManifestService.load,
    Then the viewer graph still exposes the identical check list.
    """
    # Given
    result = _build_fixture_project(
        tmp_path,
        "pgvector_openai_rag",
        project_id="project:reload-next-checks",
    )
    assert result.status == "ok"
    assert result.viewer_load_result is not None
    built_checks = (
        result.viewer_load_result.graph_view_model.recommended_next_checks
    )
    assert built_checks
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )

    # When
    reloaded = service.load(service.persist(result))

    # Then
    assert reloaded.viewer_load_result is not None
    assert (
        reloaded.viewer_load_result.graph_view_model.recommended_next_checks
        == built_checks
    )
    assert reloaded.ai_system_map is not None
    assert [
        check.id for check in reloaded.ai_system_map.recommended_next_checks
    ] == [check.id for check in built_checks]


def test_normal_build_defaults_to_one_native_v2_canonical_map(
    tmp_path: Path,
) -> None:
    # Given
    request = MapBuildRequest(project_path=tmp_path)

    # When
    result = _build(tmp_path)

    # Then
    assert request.system_map_schema_version == "ai-system-map/v2"
    assert "normalized_ai_system_map" not in MapBuildResult.model_fields
    assert result.ai_system_map is not None
    assert result.ai_system_map.schema_version == "ai-system-map/v2"
    assert result.ai_system_map.system_type == "ai_system"
    assert result.ai_system_map.source_schema_version == "ai-system-map/v2"
    assert result.active_schema_version == "ai-system-map/v2"
    assert result.source_schema_version == "ai-system-map/v2"
    assert result.operator_rollback_active is False


def test_normal_v2_artifact_has_no_legacy_or_rag_only_shape(
    tmp_path: Path,
) -> None:
    # Given
    result = _build(tmp_path)
    assert result.map_json_path is not None

    # When
    payload = json.loads(result.map_json_path.read_text(encoding="utf-8"))

    # Then
    assert payload["schema_version"] == "ai-system-map/v2"
    assert payload["system_type"] == "ai_system"
    assert payload["source_schema_version"] == "ai-system-map/v2"
    assert (
        not {
            "components_by_slot",
            "extensions",
            "reference_architecture",
            "classification",
        }
        & payload.keys()
    )
    assert all(
        component.get("canonical_type") != "slot_placeholder"
        for component in payload["components"]
    )


def test_unknown_schema_version_uses_stable_cutover_error_code() -> None:
    with pytest.raises(
        CanonicalMapLoadError,
        match="unsupported_system_map_schema_version",
    ):
        CanonicalMapLoader().load({"schema_version": "ai-system-map/v999"})


def test_build_publishes_exactly_one_canonical_v2_map_json(
    tmp_path: Path,
) -> None:
    """The single write path emits one canonical artifact.

    Given the only remaining build path,
    When a snapshot is built,
    Then exactly one ai_system_map.json is published and it is v2, with
    no sibling artifact left over from a second writer.
    """
    # Given / When
    result = _build(tmp_path)

    # Then
    assert result.map_json_path is not None
    artifact = json.loads(result.map_json_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == "ai-system-map/v2"
    json_names = [
        path.name for path in result.map_json_path.parent.glob("*.json")
    ]
    assert json_names.count("ai_system_map.json") == 1


def test_public_v1_selection_fails_before_writing_artifacts(
    tmp_path: Path,
) -> None:
    # Given
    request = MapBuildRequest(
        project_path=tmp_path / "project",
        system_map_schema_version="ai-system-map/v1",
    )

    # When
    raised = pytest.raises(
        CanonicalOutputConfigurationError,
        match="legacy_output_not_selectable",
    )

    # Then
    with raised:
        _build(tmp_path, request=request)
    assert not (tmp_path / "build").exists()


def test_operator_env_v1_fails_before_writing_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The legacy env value is no longer an escape hatch to a v1 build.

    Given SYSTOGRAPH_CANONICAL_OUTPUT_VERSION set to the legacy version,
    When a default MapBuildService builds a snapshot,
    Then construction fails with the stable
    invalid_canonical_output_version code and no artifact is written.
    """
    # Given
    monkeypatch.setenv(
        "SYSTOGRAPH_CANONICAL_OUTPUT_VERSION",
        "ai-system-map/v1",
    )

    # When
    raised = pytest.raises(
        CanonicalOutputConfigurationError,
        match="invalid_canonical_output_version",
    )

    # Then
    with raised:
        _build(tmp_path)
    assert not (tmp_path / "build").exists()


def test_operator_env_v1_prevents_app_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Web app refuses to start in the removed rollback mode.

    Given SYSTOGRAPH_CANONICAL_OUTPUT_VERSION set to the legacy version,
    When the FastAPI app is created,
    Then startup fails with invalid_canonical_output_version, so no
    process can serve requests in a mode that no longer exists.
    """
    monkeypatch.setenv(
        "SYSTOGRAPH_CANONICAL_OUTPUT_VERSION",
        "ai-system-map/v1",
    )

    with pytest.raises(
        CanonicalOutputConfigurationError,
        match="invalid_canonical_output_version",
    ):
        create_app()


def test_invalid_operator_version_prevents_app_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SYSTOGRAPH_CANONICAL_OUTPUT_VERSION",
        "ai-system-map/v999",
    )

    with pytest.raises(
        CanonicalOutputConfigurationError,
        match="invalid_canonical_output_version",
    ):
        create_app()


def test_enriched_map_build_publishes_a_v2_child_build(
    tmp_path: Path,
) -> None:
    """The enriched-map entry point has one behaviour, not two.

    Given a normal build whose canonical map is then enriched,
    When a child build is published from that map,
    Then it succeeds as a v2 build; the removed rollback branch no
    longer refuses this path with a legacy_rollback_* code.
    """
    # Given
    normal = _build(tmp_path)
    assert normal.ai_system_map is not None
    snapshot = ScanSnapshot(
        project_id="project:enriched-child",
        scan_id="scan:v2-cutover",
        generated_at=datetime(2026, 7, 17, tzinfo=UTC),
        inventory_digest="sha256:enriched-child",
        scan_result=ProjectScanResult(),
    )
    output_dir = tmp_path / "child-build"

    # When
    child = MapBuildService().build_from_enriched_map(
        snapshot,
        system_map=normal.ai_system_map,
        capability_candidates=(),
        request=MapBuildRequest(project_path=tmp_path),
        output_run=OutputRun(root_dir=output_dir),
        based_on_build_id="build:v2-cutover",
    )

    # Then
    assert child.status == "ok"
    assert child.active_schema_version == "ai-system-map/v2"
    assert child.operator_rollback_active is False
    assert child.ai_system_map is not None
    assert child.ai_system_map.schema_version == "ai-system-map/v2"
