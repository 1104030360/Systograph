from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kai_mind.core.models.analysis_history import ScanSnapshot
from kai_mind.core.models.map_build import (
    MapBuildRequest,
    MapBuildResult,
    SystemMapSchemaSelection,
)
from kai_mind.core.models.scan import OutputRun, ProjectScanResult
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.build_manifest_artifacts import digest
from kai_mind.core.services.build_manifest_service import (
    BuildArtifactLoadError,
    BuildManifestService,
)
from kai_mind.core.services.map_build_service import MapBuildService


def built_result(
    tmp_path: Path,
    *,
    schema_version: SystemMapSchemaSelection = "ai-system-map/v1",
) -> MapBuildResult:
    snapshot = ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(),
    )
    return MapBuildService().build_from_snapshot(
        snapshot,
        request=MapBuildRequest(
            project_path=tmp_path / "project",
            system_map_schema_version=schema_version,
        ),
        output_run=OutputRun(root_dir=tmp_path / "output" / "build_b1"),
        build_id="build:b1",
        build_reason="initial_scan",
    )


def test_persisted_manifest_reloads_build_from_artifact_refs(
    tmp_path: Path,
) -> None:
    state = LocalJsonStateProvider(tmp_path / "state")
    service = BuildManifestService(repository=state)
    result = built_result(tmp_path)

    manifest = service.persist(result)
    loaded = service.load(manifest)

    assert loaded.lineage == result.lineage
    assert result.viewer_load_result is not None
    assert loaded.viewer_load_result is not None
    assert loaded.viewer_load_result.loaded
    assert loaded.viewer_load_result.graph_view_model == (
        result.viewer_load_result.graph_view_model
    )
    assert set(manifest.artifact_digests) == {
        "ai_system_map.json",
        "profile_signals.json",
        "readiness_report.json",
        "call_graph.json",
        "dataflow_hints.json",
        "execution_paths.json",
        "evidence_table.json",
        "ai_system_map.md",
        "system_map.mmd",
        "execution_map.mmd",
    }


def test_manifest_reload_preserves_schema_selection_metadata(
    tmp_path: Path,
) -> None:
    state = LocalJsonStateProvider(tmp_path / "state")
    service = BuildManifestService(repository=state)
    result = built_result(tmp_path, schema_version="ai-system-map/v2")

    loaded = service.load(service.persist(result))

    assert loaded.active_schema_version == result.active_schema_version
    assert loaded.requested_schema_version == result.requested_schema_version
    assert loaded.migration_warnings == result.migration_warnings


def test_missing_profile_sidecar_degrades_without_hiding_base_graph(
    tmp_path: Path,
) -> None:
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.profile_signals_path is not None
    result.profile_signals_path.unlink()

    loaded = service.load(manifest)

    assert loaded.viewer_load_result is not None
    assert loaded.viewer_load_result.loaded
    assert loaded.profile_inference_result is None
    assert "profile_signals_missing_or_invalid" in loaded.warnings


def test_missing_readiness_sidecar_degrades_without_hiding_base_graph(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.readiness_report_path is not None
    result.readiness_report_path.unlink()

    # When
    loaded = service.load(manifest)

    # Then
    assert loaded.viewer_load_result is not None
    assert loaded.viewer_load_result.loaded
    assert loaded.readiness_report is None
    assert "readiness_report_missing_or_invalid" in loaded.warnings


def test_manifest_persist_rejects_failed_build(tmp_path: Path) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    failed = MapBuildResult(status="error", project_name="project")

    # When / Then
    with pytest.raises(
        ValueError,
        match="only successful project builds can be persisted",
    ):
        service.persist(failed)


def test_manifest_persist_rejects_missing_output_directory(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path).model_copy(update={"output_run_dir": None})

    # When / Then
    with pytest.raises(ValueError, match="build output directory is missing"):
        service.persist(result)


def test_invalid_canonical_map_fails_closed(tmp_path: Path) -> None:
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.map_json_path is not None
    result.map_json_path.write_text("{}", encoding="utf-8")

    with pytest.raises(BuildArtifactLoadError):
        service.load(manifest)


def test_semantically_invalid_canonical_map_fails_with_valid_digest(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.map_json_path is not None
    result.map_json_path.write_text("{}", encoding="utf-8")
    manifest = manifest.model_copy(
        update={
            "artifact_digests": {
                **manifest.artifact_digests,
                "ai_system_map.json": digest(result.map_json_path),
            }
        }
    )

    # When / Then
    with pytest.raises(
        BuildArtifactLoadError,
        match="canonical map is invalid",
    ):
        service.load(manifest)


def test_missing_optional_artifact_degrades_without_hiding_map(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.call_graph_path is not None
    result.call_graph_path.unlink()

    # When
    loaded = service.load(manifest)

    # Then
    assert loaded.ai_system_map is not None
    assert loaded.call_graph_path is None
    assert "optional_artifact_invalid:call_graph.json" in loaded.warnings


def test_invalid_profile_sidecar_degrades_with_valid_digest(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.profile_signals_path is not None
    result.profile_signals_path.write_text("{}", encoding="utf-8")
    manifest = manifest.model_copy(
        update={
            "artifact_digests": {
                **manifest.artifact_digests,
                "profile_signals.json": digest(result.profile_signals_path),
            }
        }
    )

    # When
    loaded = service.load(manifest)

    # Then
    assert loaded.viewer_load_result is not None
    assert loaded.viewer_load_result.loaded
    assert loaded.profile_inference_result is None
    assert "profile_signals_missing_or_invalid" in loaded.warnings


def test_invalid_readiness_sidecar_degrades_with_valid_digest(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.readiness_report_path is not None
    result.readiness_report_path.write_text("{}", encoding="utf-8")
    manifest = manifest.model_copy(
        update={
            "artifact_digests": {
                **manifest.artifact_digests,
                "readiness_report.json": digest(result.readiness_report_path),
            }
        }
    )

    # When
    loaded = service.load(manifest)

    # Then
    assert loaded.ai_system_map is not None
    assert loaded.readiness_report is None
    assert "readiness_report_missing_or_invalid" in loaded.warnings


def test_profile_sidecar_scope_mismatch_degrades_with_valid_digest(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.profile_signals_path is not None
    payload = json.loads(
        result.profile_signals_path.read_text(encoding="utf-8")
    )
    payload["build_id"] = "build:other"
    payload["generated_from_build_id"] = "build:other"
    for assessment in payload["reference_capability_assessments"]:
        assessment["build_id"] = "build:other"
    for profile in payload["profiles"]:
        profile["build_id"] = "build:other"
    result.profile_signals_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    manifest = manifest.model_copy(
        update={
            "artifact_digests": {
                **manifest.artifact_digests,
                "profile_signals.json": digest(result.profile_signals_path),
            }
        }
    )

    # When
    loaded = service.load(manifest)

    # Then
    assert loaded.profile_inference_result is None
    assert "profile_signals_scope_mismatch" in loaded.warnings


def test_readiness_sidecar_scope_mismatch_degrades_with_valid_digest(
    tmp_path: Path,
) -> None:
    # Given
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    manifest = service.persist(result)
    assert result.readiness_report_path is not None
    payload = json.loads(
        result.readiness_report_path.read_text(encoding="utf-8")
    )
    payload["scan_id"] = "scan:other"
    result.readiness_report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    manifest = manifest.model_copy(
        update={
            "artifact_digests": {
                **manifest.artifact_digests,
                "readiness_report.json": digest(result.readiness_report_path),
            }
        }
    )

    # When
    loaded = service.load(manifest)

    # Then
    assert loaded.readiness_report is None
    assert "readiness_report_scope_mismatch" in loaded.warnings


def test_persist_rejects_cross_artifact_scope_mismatch(tmp_path: Path) -> None:
    service = BuildManifestService(
        repository=LocalJsonStateProvider(tmp_path / "state")
    )
    result = built_result(tmp_path)
    assert result.readiness_report_path is not None
    payload = json.loads(
        result.readiness_report_path.read_text(encoding="utf-8")
    )
    payload["build_id"] = "build:other"
    result.readiness_report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="scope mismatch"):
        service.persist(result)
