from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionService,
)
from kai_mind.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from kai_mind.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from kai_mind.core.services.minimal_viewer_projection_service import (
    MinimalViewerProjectionService,
)
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.rag_template_service import RagTemplateService
from kai_mind.core.services.risk_hint_service import RiskHintService
from kai_mind.core.services.system_map_normalize_service import (
    SystemMapNormalizeService,
)


def build_system_map(fixture_name: str) -> RagSystemMap:
    project_root = rag_project_fixture_path(fixture_name)
    raw_scan = ProjectScanService().scan(project_root)
    template = RagTemplateService.load("rag-core-v1")
    components = ComponentDetectionService().detect(
        template=template,
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
    )
    endpoints = EndpointDetectionService().detect(
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
        components=components,
    )
    risk_hints = RiskHintService().derive(
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
        issues=raw_scan.issues,
        components=components,
        endpoints=endpoints,
    )
    flows = FlowDerivationService().derive(
        template=template,
        components=components,
    )
    return SystemMapNormalizeService().normalize(
        project_name=fixture_name,
        raw_scan=raw_scan,
        template=template,
        components=components,
        endpoints=endpoints,
        flows=flows,
        risk_hints=risk_hints,
    )


def test_minimal_projection_indexes_canonical_evidence_and_risks() -> None:
    system_map = build_system_map("basic_qdrant_ollama_rag")

    viewer_load_result = MinimalViewerProjectionService().build(
        system_map,
        map_json_path=Path("outputs/ai_system_map.json"),
    )

    graph = viewer_load_result.graph_view_model
    assert viewer_load_result.loaded
    assert viewer_load_result.error_reason is None
    assert graph.source_schema_version == "ai-system-map/v1"
    assert graph.nodes
    assert graph.edges
    assert graph.details.evidence_by_id == {
        evidence.id: evidence.model_dump(mode="json")
        for evidence in system_map.evidence
    }
    assert graph.details.risk_hints_by_id == {
        risk.id: risk.model_dump(mode="json") for risk in system_map.risk_hints
    }
    assert isinstance(graph.filters.available, list)

    vector_node = next(
        node for node in graph.nodes if node.slot == "vector_store"
    )
    assert vector_node.source_id == "vector_store"
    assert vector_node.evidence_ids
    assert vector_node.risk_hint_ids


def test_projection_does_not_mutate_canonical_map() -> None:
    system_map = build_system_map("basic_qdrant_ollama_rag")

    MinimalViewerProjectionService().build(
        system_map,
        map_json_path=Path("outputs/ai_system_map.json"),
    )

    data = system_map.model_dump(mode="json")
    assert "viewer_load_result" not in data
    assert "graph_view_model" not in data
