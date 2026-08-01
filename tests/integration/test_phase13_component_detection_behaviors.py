from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.rag_template_service import RagTemplateService


def detect_fixture(name: str) -> ComponentDetectionResult:
    raw_scan = ProjectScanService().scan(rag_project_fixture_path(name))
    template = RagTemplateService.load("rag-core-v1")
    return ComponentDetectionService().detect(
        template=template,
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
    )


def test_basic_qdrant_ollama_fixture_detects_core_components() -> None:
    result = detect_fixture("basic_qdrant_ollama_rag")

    assert result.components_by_slot["vector_store"].status == "detected"
    assert result.components_by_slot["vector_store"].instances[0].name == (
        "Qdrant"
    )
    assert result.components_by_slot["llm"].status == "detected"
    assert result.components_by_slot["llm"].instances[0].name == "Ollama"
    assert result.components_by_slot["retriever"].status == "detected"
    assert (
        result.components_by_slot["app_api_or_orchestrator"].status
        == "detected"
    )
    assert (
        result.components_by_slot["citation_or_response_composer"].status
        == "missing"
    )


def test_custom_router_fixture_preserves_unmapped_component() -> None:
    result = detect_fixture("custom_router_rag")

    assert result.components_by_slot["retriever"].status == "missing"
    assert result.unmapped_components
    assert any(
        "router" in component.observed_kind
        or "router" in component.reason.lower()
        for component in result.unmapped_components
    )


def test_reranker_fixture_creates_non_baseline_confirmation_item() -> None:
    result = detect_fixture("reranker_extension_rag")

    assert result.unmapped_components
    assert result.unmapped_components[0].observed_kind == "reranker_candidate"
    assert "confirm_mapping" in result.unmapped_components[0].suggested_actions


def test_qdrant_provider_config_fixture_supports_vector_store_mapping() -> (
    None
):
    raw_scan = ProjectScanService().scan(
        rag_project_fixture_path("graph_rag_extension_rag")
    )
    template = RagTemplateService.load("rag-core-v1")
    result = ComponentDetectionService().detect(
        template=template,
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
    )
    config_evidence_ids = {
        evidence.id
        for evidence in raw_scan.evidence
        if evidence.file == "config.yaml"
        and evidence.path == "vector_store.provider"
        and evidence.value == "qdrant"
    }

    vector_store = result.components_by_slot["vector_store"]
    qdrant_instances = [
        instance
        for instance in vector_store.instances
        if instance.provider == "qdrant"
    ]
    assert vector_store.status == "detected"
    assert qdrant_instances
    assert config_evidence_ids
    assert config_evidence_ids <= set(qdrant_instances[0].evidence_ids)


def test_unsupported_provider_config_fixture_stays_missing() -> None:
    result = detect_fixture("lancedb_or_chroma_local_rag")

    assert result.components_by_slot["vector_store"].status == "missing"
    assert result.components_by_slot["llm"].status == "missing"
    assert result.components_by_slot["embedding_model"].status == "missing"
