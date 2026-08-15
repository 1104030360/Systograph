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


def test_lancedb_local_stack_is_detected_end_to_end() -> None:
    result = detect_fixture("lancedb_or_chroma_local_rag")

    # `import lancedb` is unambiguous client identity in the package
    # layer, so the embedded vector store is real evidence -- as is the
    # fixture's direct ollama.embeddings(...) call for the embedding
    # model and the local runtime.
    vector_store = result.components_by_slot["vector_store"]
    assert vector_store.status == "detected"
    assert [instance.provider for instance in vector_store.instances] == [
        "lancedb"
    ]
    assert result.components_by_slot["llm"].status == "detected"
    assert result.components_by_slot["llm"].instances[0].name == "Ollama"
    assert result.components_by_slot["embedding_model"].status == "detected"
    assert (
        result.components_by_slot["embedding_model"].instances[0].provider
        == "ollama"
    )


def test_package_import_evidence_merges_into_existing_components() -> None:
    # basic_qdrant_ollama_rag has `import ollama` and
    # `from qdrant_client import QdrantClient` on top of docker and
    # code-pattern evidence. The package identity layer must merge its
    # import evidence into the SAME components -- never duplicate them.
    raw_scan = ProjectScanService().scan(
        rag_project_fixture_path("basic_qdrant_ollama_rag")
    )
    template = RagTemplateService.load("rag-core-v1")
    result = ComponentDetectionService().detect(
        template=template,
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
    )

    ollama_instances = [
        instance
        for instance in result.components_by_slot["llm"].instances
        if instance.provider == "ollama"
    ]
    qdrant_instances = [
        instance
        for instance in result.components_by_slot["vector_store"].instances
        if instance.provider == "qdrant"
    ]
    assert len(ollama_instances) == 1
    assert len(qdrant_instances) == 1

    import_evidence = {
        evidence.id: evidence
        for evidence in raw_scan.evidence
        if evidence.rule_id == "ast_external_import"
    }
    ollama_import_ids = {
        evidence_id
        for evidence_id, evidence in import_evidence.items()
        if (evidence.value or "").split(".", 1)[0] == "ollama"
    }
    qdrant_import_ids = {
        evidence_id
        for evidence_id, evidence in import_evidence.items()
        if (evidence.value or "").split(".", 1)[0] == "qdrant_client"
    }
    assert ollama_import_ids
    assert qdrant_import_ids
    assert ollama_import_ids <= set(ollama_instances[0].evidence_ids)
    assert qdrant_import_ids <= set(qdrant_instances[0].evidence_ids)
    # Evidence families stay merged: the components keep non-import
    # evidence (docker / code pattern) next to the import declarations.
    assert set(ollama_instances[0].evidence_ids) - ollama_import_ids
    assert set(qdrant_instances[0].evidence_ids) - qdrant_import_ids
