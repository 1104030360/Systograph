from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.models.errors import PreconditionFailureReason
from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.models.scan import ProjectScanResult, ScanFact
from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
)
from kai_mind.core.models.template import RagTemplate
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingService,
)
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


def fixed_clock() -> datetime:
    return datetime(2026, 6, 5, 9, 30, 0, tzinfo=UTC)


class EmptyProjectScanService(ProjectScanService):
    def scan(self, project_root: Path) -> ProjectScanResult:
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
            extensions=[],
            unmapped_components=[],
        )


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
    assert result.viewer_load_result is not None
    assert result.viewer_load_result.loaded
    assert result.viewer_load_result.graph_view_model.nodes

    artifact_data = json.loads(
        result.map_json_path.read_text(encoding="utf-8")
    )
    validated = SystemMapValidationService().validate(artifact_data)
    assert validated.schema_version == "ai-system-map/v1"
    assert "viewer_load_result" not in artifact_data
    assert "graph_view_model" not in artifact_data

    markdown = result.map_markdown_path.read_text(encoding="utf-8")
    assert markdown.startswith("# KAI-Mind System Map\n")
    assert "## Slot Coverage" in markdown
    assert "## Recommended Next Checks" in markdown


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
    vector_store = result.ai_system_map.components_by_slot["vector_store"]
    assert vector_store.status == "detected"
    assert vector_store.instances[0].name == "Injected Vector Store"
