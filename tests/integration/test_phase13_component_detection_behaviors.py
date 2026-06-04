from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.rag_template_service import RagTemplateService


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


def test_reranker_fixture_creates_extension_candidate() -> None:
    result = detect_fixture("reranker_extension_rag")

    assert result.extensions
    assert result.extensions[0].kind == "reranker"
    assert result.extensions[0].status == "candidate"
