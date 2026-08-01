from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.errors import PreconditionFailureReason
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.scan import OutputRun, ProjectScanResult, ScanFact
from systograph.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
)
from systograph.core.models.template import RagTemplate
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingService,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.project_scan_service import (
    InventoryPolicyOverlay,
    ProjectScanService,
)
from systograph.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)


def fixed_clock() -> datetime:
    return datetime(2026, 6, 5, 9, 30, 0, tzinfo=UTC)


class EmptyProjectScanService(ProjectScanService):
    def scan(
        self,
        project_root: Path,
        *,
        inventory_policy: InventoryPolicyOverlay | None = None,
    ) -> ProjectScanResult:
        return ProjectScanResult(
            evidence=[
                Evidence(
                    id="evidence:custom-detector",
                    kind="custom_signal",
                    file="src/custom.py",
                    path="custom.detector",
                    value="Injected Vector Store",
                    rule_id="custom_vector_store_rule",
                )
            ],
            files_scanned=1,
        )


class InjectedVectorStoreDetector(ComponentDetectionService):
    def __init__(self) -> None:
        super().__init__()
        self.called = False

    def detect(
        self,
        *,
        template: RagTemplate,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
    ) -> ComponentDetectionResult:
        self.called = True
        slots = {
            slot.id: ComponentSlot(
                slot=slot.id,
                required_for_rag=slot.required_for_rag_hint,
                status="missing",
                instances=[],
            )
            for slot in template.slots
        }
        slots["vector_store"] = ComponentSlot(
            slot="vector_store",
            required_for_rag=True,
            status="detected",
            instances=[
                ComponentInstance(
                    id="component:vector_store:injected",
                    slot="vector_store",
                    kind="vector_db",
                    name="Injected Vector Store",
                    provider="custom",
                    evidence_ids=["evidence:custom-detector"],
                )
            ],
        )
        return ComponentDetectionResult(
            components_by_slot=slots,
            unmapped_components=[],
        )


class RecordingValidationService(SystemMapV2ValidationService):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[Mapping[str, Any]] = []

    def validate(self, data: Mapping[str, Any]) -> AiSystemMapV2:
        self.calls.append(data)
        return super().validate(data)


class FailingSiblingProvider(OutputArtifactProvider):
    def write_readiness_report(
        self,
        report: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        raise RuntimeError("forced sibling publish failure")


def test_map_build_service_builds_valid_canonical_map_and_viewer_payload(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    result = MapBuildService().build(
        MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "outputs",
        )
    )

    assert result.status == "ok"
    assert result.project_name == "basic_qdrant_ollama_rag"
    assert result.map_error_path is None
    assert result.map_json_path is not None
    assert result.map_json_path.is_file()
    assert result.map_markdown_path is not None
    assert result.map_markdown_path.is_file()
    sibling_paths = (
        result.profile_signals_path,
        result.readiness_report_path,
        result.call_graph_path,
        result.dataflow_hints_path,
        result.execution_paths_path,
        result.evidence_table_path,
        result.system_map_mermaid_path,
        result.execution_map_mermaid_path,
    )
    assert all(path is not None and path.is_file() for path in sibling_paths)
    assert result.profile_inference_result is not None
    assert result.readiness_report is not None
    assert result.profile_inference_result.build_id == (
        result.readiness_report.build_id
    )
    assert result.profile_inference_result.scan_id == (
        result.readiness_report.scan_id
    )
    assert result.viewer_load_result is not None
    assert result.viewer_load_result.loaded
    assert result.viewer_load_result.graph_view_model.nodes
    graph = result.viewer_load_result.graph_view_model
    profile = result.profile_inference_result
    assert graph.scan_id == profile.scan_id
    assert graph.build_id == profile.build_id
    assert graph.generated_from_build_id == profile.build_id

    artifact_data = json.loads(
        result.map_json_path.read_text(encoding="utf-8")
    )
    loaded = CanonicalMapLoader().load(artifact_data)
    assert loaded.active_schema_version == "ai-system-map/v2"
    assert loaded.normalized.schema_version == "ai-system-map/v2"
    assert "viewer_load_result" not in artifact_data
    assert "graph_view_model" not in artifact_data

    markdown = result.map_markdown_path.read_text(encoding="utf-8")
    assert markdown.startswith("# Systograph System Map\n")
    assert "## Nodes" in markdown
    assert "## Topology Edges" in markdown
    graph = result.viewer_load_result.graph_view_model
    assert result.system_map_mermaid_path is not None
    mermaid = result.system_map_mermaid_path.read_text(encoding="utf-8")
    assert all(node.id in markdown for node in graph.nodes)
    assert all(edge.id in markdown for edge in graph.edges)
    assert all(node.id in mermaid for node in graph.nodes)
    assert all(edge.id in mermaid for edge in graph.edges)


def test_map_build_failure_removes_partial_public_siblings(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    service = MapBuildService(
        output_artifact_provider=FailingSiblingProvider()
    )

    with pytest.raises(RuntimeError, match="forced sibling publish failure"):
        service.build(
            MapBuildRequest(
                project_path=rag_project_fixture_path(
                    "basic_qdrant_ollama_rag"
                ),
                output=output_dir,
            )
        )

    assert not output_dir.exists() or not any(output_dir.iterdir())


def test_map_build_service_validates_after_request_options_by_default(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    validation_service = RecordingValidationService()

    result = MapBuildService(validation_service=validation_service).build(
        MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "outputs",
        )
    )

    assert result.status == "ok"
    assert len(validation_service.calls) == 1
    assert validation_service.calls[0]["project"]["path_mode"] == "redacted"


def test_map_build_service_keeps_v2_path_safe_when_options_are_modified(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    validation_service = RecordingValidationService()

    result = MapBuildService(validation_service=validation_service).build(
        MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "outputs",
            redact_root_path=False,
            no_snippets=True,
        )
    )

    assert result.status == "ok"
    assert len(validation_service.calls) == 1
    validated_data = validation_service.calls[0]
    assert validated_data["project"]["path_mode"] == "redacted"
    assert all(
        item.get("extract_summary") is None
        for item in validated_data["evidence"]
    )


def test_map_build_service_missing_project_writes_map_error_only(
    tmp_path: Path,
) -> None:
    missing_project = tmp_path / "missing-project"

    result = MapBuildService().build(
        MapBuildRequest(
            project_path=missing_project,
            output=tmp_path / "outputs",
        )
    )

    assert result.status == "error"
    assert result.error is not None
    assert (
        result.error.failure_reason
        == PreconditionFailureReason.PROJECT_PATH_NOT_FOUND
    )
    assert result.map_json_path is None
    assert result.map_markdown_path is None
    assert result.map_error_path == tmp_path / "outputs" / "map-error.md"
    assert result.map_error_path.is_file()
    assert not (tmp_path / "outputs" / "ai_system_map.json").exists()
    assert not (tmp_path / "outputs" / "ai_system_map.md").exists()
    assert not (tmp_path / "outputs" / "profile_signals.json").exists()
    assert not (tmp_path / "outputs" / "readiness_report.json").exists()


def test_map_build_service_uses_timestamped_output_run_when_artifact_exists(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "ai_system_map.json").write_text("{}", encoding="utf-8")

    result = MapBuildService(
        output_artifact_provider=OutputArtifactProvider(clock=fixed_clock)
    ).build(MapBuildRequest(project_path=project_root, output=output_dir))

    assert result.status == "ok"
    assert result.output_run_dir == output_dir / "20260605T093000"
    assert result.map_json_path == (
        output_dir / "20260605T093000" / "ai_system_map.json"
    )
    assert result.map_markdown_path == (
        output_dir / "20260605T093000" / "ai_system_map.md"
    )


def test_map_build_service_keeps_secret_values_masked(tmp_path: Path) -> None:
    project_root = rag_project_fixture_path("openai_external_provider_rag")

    result = MapBuildService().build(
        MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "outputs",
        )
    )

    assert result.status == "ok"
    assert result.map_json_path is not None
    assert result.map_markdown_path is not None
    artifact_text = result.map_json_path.read_text(encoding="utf-8")
    markdown_text = result.map_markdown_path.read_text(encoding="utf-8")
    assert "sk-test" not in artifact_text
    assert "sk-test" not in markdown_text
    assert "[MASKED]" in artifact_text or "..." in artifact_text


def test_map_build_masks_credentials_across_all_output_models(
    tmp_path: Path,
) -> None:
    project_root = rag_project_fixture_path("secret_masking_regression_rag")
    raw_values = {
        "synthetic-db-pass-138",
        "synthetic-short-pass-138",
        "synthetic-api-key-138",
        "synthetic-url-pass-138",
        "synthetic-openai-pass-138",
    }

    result = MapBuildService().build(
        MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "outputs",
        )
    )

    assert result.status == "ok"
    assert result.map_json_path is not None
    assert result.map_markdown_path is not None
    assert result.ai_system_map is not None
    assert result.viewer_load_result is not None

    serialized_outputs = [
        result.map_json_path.read_text(encoding="utf-8"),
        result.map_markdown_path.read_text(encoding="utf-8"),
        json.dumps(result.model_dump(mode="json"), default=str),
        json.dumps(result.ai_system_map.model_dump(mode="json")),
        json.dumps(result.viewer_load_result.model_dump(mode="json")),
    ]
    combined = "\n".join(serialized_outputs)

    for raw_value in raw_values:
        assert raw_value not in combined
    assert "[MASKED]" in combined


def test_project_mapping_preserves_injected_component_detector(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    detector = InjectedVectorStoreDetector()

    result = MapBuildService(
        project_scan_service=EmptyProjectScanService(),
        component_detection_service=detector,
        manual_mapping_service=ManualMappingService(
            repository=InMemoryManualMappingRepository(),
            allowed_slots={"vector_store"},
        ),
    ).build(
        MapBuildRequest(
            project_path=project_root,
            output=tmp_path / "outputs",
        ),
        project_id="project:demo",
    )

    assert result.status == "ok"
    assert detector.called
    assert result.ai_system_map is not None
    vector_store = next(
        component
        for component in result.ai_system_map.components
        if component.metadata.get("legacy_slot") == "vector_store"
    )
    assert vector_store.status == "detected"
    assert vector_store.display_name == "Injected Vector Store"
